from rdkit import DataStructs
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.rdmolops import RemoveStereochemistry
from rdkit.Chem.Fingerprints import FingerprintMols
from rdkit.Chem.Descriptors import HeavyAtomMolWt
from rdkit.Chem.SaltRemover import SaltRemover


#Putting "O" in here will unify hydrates, like morphine and morphine monohydrate (called morphine by mesh!)
remover = SaltRemover(defnData='[Cl,Br,K,I,Na,O]')

chems = []
n = 0
with open('smiles.txt','r') as inf, open('simpler_nodes.csv','w') as outf_nodes, open('simpler_edges.csv','w') as outf_edges:
    # write out the header records for KGX
    outf_nodes.write(f'id,name,smiles,category\n')
    outf_edges.write(f'subject,edge_label,object\n')

    # used for the
    gamma_counter = 0

    for line in inf:
        x = line.strip().split('\t')

        if x[1] == 'None':
            continue
        else:
            name = x[1]

        n+=1

#        if n % 10000 == 0:
            #print(n)

        cid = x[0]

        #this set of identifiers causes rdkit to segfault :(
        # given the number of things in the list, a better strategy than run it till it dies, and try
        # again is probably advisable
        #if cid in ['CHEBI:17627', 'CHEBI:50385','CHEBI:18140','CHEBI:38277','CHEBI:50162',
        #           'CHEBI:29297','CHEBI:29293','CHEBI:133488','CHEBI:30158','CHEBI:51220',
        ##           'CHEBI:30470','CHEBI:36301','CHEBI:38284','CHEBI:48998','CHEBI:37189',
        #           'CHEBI:60532','CHEBI:51221','CHEBI:29416', 'CHEBI:36163','CHEBI:29296',
        #           'CHEBI:51508','CHEBI:30665','CHEBI:29886','CHEBI:85715','CHEBI:49851',
        #           'CHEBI:30197','CHEBI:30125','CHEBI:37856','CHEBI:38283','CHEBI:10098',
        #           'CHEBI:132769','CHEBI:133489','CHEBI:134067','CHEBI:141330','CHEBI:15432',
        #           'CHEBI:26355','CHEBI:28163','CHEBI:29295','CHEBI:29417','CHEBI:29418',
        #           'CHEBI:29422','CHEBI:29440','CHEBI:29796','CHEBI:29880','CHEBI:30126',
        #           'CHEBI:30238']:
        #    continue

        orig_smiles = x[2]

        if orig_smiles == '[empty]':
            continue
        try:
            mol = Chem.MolFromSmiles(orig_smiles)
        except Exception as e:
            print(f"error with {orig_smiles}. Proceeding")
            continue

        if mol is None:
            #Couldn't parse
            continue
        try:
            #print(f'{cid}\t{smiles}')
            molp = rdMolStandardize.ChargeParent(mol)
            RemoveStereochemistry(molp)
            new_smiles = Chem.MolToSmiles(molp)
            #chems.append(chem)

            # outf_nodes.write(f'id,name,smiles,category\n')
            # outf_edges.write(f'subject,edge_label,object\n')

            if orig_smiles != new_smiles:
                print(f'{cid} not equal. old:{orig_smiles} new:{new_smiles}')

                outf_nodes.write(f"{cid},\"{name}\",\"{orig_smiles}\",chemical_substance\n")

                outf_edges.write(f'{cid},equivalent_smiles,gamma_smiles:{gamma_counter}\n')

                outf_nodes.write(f"gamma_smiles:{gamma_counter},\"{name}\",\"{new_smiles}\",chemical_substance\n")

                gamma_counter = gamma_counter+1

        except Exception as e:
            print(f"error with {x}")
            #exit()
