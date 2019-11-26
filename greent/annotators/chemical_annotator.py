#import requests
import logging
from greent.annotators.annotator import Annotator
from greent.annotators.util.async_sparql_client import TripleStoreAsync
from greent.util import Text, LoggingUtil
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.rdmolops import RemoveStereochemistry
import asyncio

logger = LoggingUtil.init_logging(__name__, level=logging.DEBUG, format='medium')

class ChemicalAnnotator(Annotator):
    def __init__(self, rosetta):
        super().__init__(rosetta)
        
        self.prefix_source_mapping = {
            'CHEMBL': self.get_chembl_data, 
            'CHEBI' : self.get_chebi_data,
            'KEGG' : self.get_kegg_data,
            'PUBCHEM': self.get_pubchem_data,
            'DRUGBANK': self.get_mychem_data,
            'KEGG.COMPOUND':self.get_kegg_data
            # 'INCHIKEY':self.get_inchikey_data
        }
        self.tripleStore = TripleStoreAsync('https://stars-app.renci.org/uberongraph/sparql')
        

    async def get_chembl_data(self, chembl_id):
        """
        Fetches chembl data from ebi.ac.uk
        """
        conf = self.get_prefix_config('CHEMBL')
        keys_of_interest = conf['keys']
        suffix = Text.un_curie(chembl_id)
        url_part = f'{suffix}.json'
        response_json = await self.async_get_json(conf['url'] + url_part)
        #There are some chembl id's that 404, leading to an empty response
        if len(response_json) == 0:
            return response_json
        return self.extract_chembl_data(response_json, keys_of_interest)
        
    def extract_chembl_data(self, chembl_raw, keys_of_interest=[]):
        """
        Extracts interesting data from chembl raw response.
        """
        extracted = {keys_of_interest[key] : \
                    self.convert_data_to_primitives(chembl_raw[key]) \
                    for key in keys_of_interest if key in chembl_raw.keys()
                    }
        
        if len(keys_of_interest) != len(extracted.keys()):
            logger.warn(f"All keys were not annotated for {chembl_raw['molecule_chembl_id']}")
        
        return extracted

    async def get_chebi_data(self, chebi_id):
        """
        Gets cebi data from onto.renci.org 
        """
        conf = self.get_prefix_config('CHEBI')
        url = conf['url'] + chebi_id
        chebi_raw = await self.async_get_json(url)
        chebi_roles = await self.get_chemical_roles(chebi_id)
        chebi_extract = self.extract_chebi_data(chebi_raw, conf['keys'])
        chebi_extract.update({x['role_label']: True for x in chebi_roles[chebi_id]})
        return chebi_extract

    def extract_chebi_data(self, chebi_raw, keys_of_interest):
        """
        restructures chebi raw data
        """
        extract = {}
        if 'all_properties' in chebi_raw and 'property_value' in chebi_raw['all_properties']:
            for prop in chebi_raw['all_properties']['property_value']:
                prop_parts = prop.split(' ')
                prop_name = prop_parts[0].split('/')[-1]
                prop_value = prop_parts[1].strip('"')
                if prop_name in keys_of_interest:
                    # handle the smiles value.
                    if prop_name == 'smiles':
                        # save the canonical, original and simple versions of the smiles
                        prop_value, extract[keys_of_interest['orig_smiles']], extract[keys_of_interest['simple_smiles']] = self.convert_value_to_smiles(prop_value)

                    extract[keys_of_interest[prop_name]] = prop_value
        return extract
          
    async def get_kegg_data(self, kegg_id):
        conf = self.get_prefix_config('KEGG')
        kegg_c_id = Text.un_curie(kegg_id)
        url = conf['url'] + kegg_c_id 
        response = await self.async_get_text(url)
        kegg_dict = self.parse_flat_file_to_dict(response)
        return self.extract_kegg_data(kegg_dict, conf['keys'])

    def extract_kegg_data(self, kegg_dict, keys_of_interest):
        extracted = {keys_of_interest[key] : \
            self.convert_data_to_primitives(kegg_dict[key]) \
            for key in keys_of_interest if key in kegg_dict.keys()}
        #if len(keys_of_interest) != len(extracted.keys()):
        #    logger.warn(f"All keys were not annotated for {kegg_dict['ENTRY']}")
        return extracted

    async def get_inchikey_data(self, inchikey_id):
        conf = self.get_prefix_config('INCHIKEY')
        inchikey_c_id = Text.un_curie(inchikey_id) 
        url = conf['url'] + inchikey_c_id
        response = await self.async_get_text(url)
        inchikey_dict = self.parse_flat_file_to_dict(response)
        return self.extract_inchikey_data(inchikey_dict, conf['keys'])

    def extract_inchikey_data(self, inchikey_dict, keys_of_interest):
        extracted = {keys_of_interest[key] : \
            self.convert_data_to_primitives(inchikey_dict[key]) \
            for key in keys_of_interest if key in inchikey_dict.keys()}
        if len(keys_of_interest) != len(extracted.keys()):
            logger.warn(f"All keys were not annotated for {inchikey_dict['ENTRY']}")
        return extracted

    def parse_flat_file_to_dict(self, raw):
        new_dict = {}
        lines = raw.split('\n')
        current_key = ''
        for line in lines:
            if line == '///':
                break # last line break
            if line and len(line) > 0 and line.startswith(' ') :
                line.strip()
                new_dict[current_key].append(line)
            else:
                words = line.split(' ')
                current_key = words[0].strip(' ')
                new_dict[current_key] = [' '.join(words[1:]).strip()]
        return new_dict


    async def get_chemical_roles(self, chebi_id):
        """
        Gets all the roles assigned to a chebi id. Should return along result along chebi_id,
        useful when making bulk request concurrently to keep track.
        """
        text = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX has_role: <http://purl.obolibrary.org/obo/RO_0000087>
        PREFIX chemical_entity: <http://purl.obolibrary.org/obo/CHEBI_24431>
        PREFIX CHEBI: <http://purl.obolibrary.org/obo/CHEBI_>
        SELECT DISTINCT ?role_label
        from <http://reasoner.renci.org/ontology>
        from <http://reasoner.renci.org/redundant>
        where {
            $chebi_id has_role: ?role.
            ?role rdfs:label ?role_label.
            GRAPH <http://reasoner.renci.org/ontology/closure> {
                ?role rdfs:subClassOf CHEBI:50906.
            }
        }
        """
        query_result = await self.tripleStore.async_query_template(
            inputs = {'chebi_id': chebi_id},
            outputs = [ 'role_label' ],
            template_text = text
        )        
        for r in query_result:
            r['role_label'] = Text.snakify(r['role_label'])
        return {chebi_id: query_result}


    async def get_pubchem_data(self, pubchem_id, retries = 0):
        """
        Gets pubchem annotations.
        """ 
        conf = self.get_prefix_config('PUBCHEM')
        url = conf['url'] + pubchem_id.split(':')[-1]
        headers = {
            'Accept': 'application/json'
        }
        result = await self.async_get_raw_response(url, headers= headers)
        # async with result as result_json:
        result_json = result['json']
        # pubmed api blocks if too many req are sent
        throttle = result['headers']['X-Throttling-Control']
        throttle_warnings = { Text.snakify(value.split(':')[0].lower()) : value.split(':')[1] for value in throttle.split(',') if ':' in value }
        if 'Yellow' in throttle_warnings['request_time_status'] or 'Yellow' in throttle_warnings['request_count_status']:
            logger.warn('Pubchem requests reached Yellow')
            await asyncio.sleep(0.5) 
        if 'Red' in throttle_warnings['request_time_status'] or 'Red' in throttle_warnings['request_count_status']:
            logger.warn('Pubchem requests reached RED')
            await asyncio.sleep(2)
        if 'Black' in throttle_warnings['request_time_status'] or 'Black' in throttle_warnings['request_count_status']:
            sleep_sec = 3 * ( retries + 1 ) # 
            logger.error(f'Pubchem request blocked, sleeping {sleep_sec} seconds, no of retries {retries}')
            await asyncio.sleep(sleep_sec)
            # repeat call if retries has changed till 3 
            if retries < 3:
                return await self.get_pubchem_data(pubchem_id, retries + 1)
            else:
                # exceeding retries return {}
                logger.warn(f'retry limit exceed for {pubchem_id} , returning empty')
                return {}
        return self.extract_pubchem_data(result_json, conf['keys'])

    def extract_pubchem_data(self, pubchem_raw, keys_of_interest = []):
        """
        Extracts pubchem data.
        """
        result = {}
        if 'PC_Compounds' in pubchem_raw:    
            for compound in pubchem_raw['PC_Compounds']:
                #I beileve we will have one in the array,
                for prop in compound['props']:
                    label = prop['urn']['label']
                    if label in keys_of_interest:
                        values = [prop['value'][v] for v in prop['value'].keys()]

                        prop_value = values[0] if len(values) == 1 else values

                        # handle the smiles value.
                        if label == 'SMILES':
                            # save the canonical, original and simple versions of the smiles
                            prop_value, result[keys_of_interest['orig_smiles']], result[keys_of_interest['simple_smiles']] = self.convert_value_to_smiles(prop_value)

                        # save the value
                        result[keys_of_interest[label]] = prop_value
        else:
            logger.error(f"got this : {pubchem_raw} for pubchem")
        return result

    #################
    # convert_to_smiles_values(self, orig_smiles)
    # return
    #   'canonical_smiles', the canonical smiles
    #   'orig_smiles' the untouched raw data element value from the source
    #   'simple_smiles' the simplified smiles
    ###############
    def convert_to_smiles_values(self, orig_smiles: str) -> (str, str, str):
        try:
            # did we get a good value
            if type(orig_smiles) == type(str) and orig_smiles != '':
                # load the raw smiles value into RDKit and get the canonical version
                mol = Chem.MolFromSmiles(orig_smiles)
                canonical_smiles = Chem.MolToSmiles(mol)

                # simplify the smiles value
                molp = rdMolStandardize.ChargeParent(mol)
                RemoveStereochemistry(molp)
                simple_smiles = Chem.MolToSmiles(molp)

                logger.debug(f'convert_to_smiles_values({orig_smiles}): {canonical_smiles}, {orig_smiles}, {simple_smiles}')
            else:
                logger.error(f'convert_to_smiles_values({orig_smiles}) invalid input.')
        except Exception as e:
            logger.error(f'convert_to_smiles_values({orig_smiles}) exception detected.')
            logger.exception(e)
            return '', '', ''

        # return to the caller
        return canonical_smiles, orig_smiles, simple_smiles

    def extract_mychem_data(self, mychem_raw, keys_of_interest = []):
        response = {}

        if 'drugbank' in mychem_raw:
            for k in keys_of_interest:
                for key in k:    
                    outter_key, inner_key = key.split('.')
                    if inner_key in mychem_raw[outter_key]:
                        cats = []
                        if inner_key == 'categories':                           
                            cats = []
                            data = mychem_raw[outter_key][inner_key]
                            if type(data) == type([]):
                                cats = [x['category'] for x in mychem_raw[outter_key][inner_key]]
                            elif type(data) == type({}): 
                                cats = [data['category']]
                            else:
                                cats = [data]
                            response[key] = cats   
                            continue                                             
                        response[key] = mychem_raw[outter_key][inner_key]    
            if 'groups' in mychem_raw['drugbank']:
                groups = {}
                if type(mychem_raw['drugbank']['groups']) == type([]):
                    groups = {f'drugbank.{g}': True 
                                for g in mychem_raw['drugbank']['groups']
                            }
                else:
                    groups = {
                        f"drugbank.{mychem_raw['drugbank']['groups']}" : True
                    }
                response.update(groups)
        return response


    async def get_mychem_data(self, mychem_id):
        """
        Gets Mychem.info annotations.
        """
        conf = self.get_prefix_config('MYCHEM')
        y = []
        for k in conf['keys']:
            for m in k:
                y.append(k[m]['source'])
        # y = [conf['keys'][x][k]['source'] for k in x for x in conf['keys']]
        fields = ','.join(y)
        url = conf['url'] + Text.un_curie(mychem_id) + '?fields='  + fields
        headers = {
            'Accept': 'application/json'
        }
        result = await self.async_get_json(url, headers= headers)
        result = result
        return self.extract_mychem_data(result, conf['keys'])
