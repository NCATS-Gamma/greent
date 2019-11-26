from neo4j import GraphDatabase
import os

# Maybe make this a notebook?

def get_driver(url):
    driver = GraphDatabase.driver(url, auth=("neo4j", os.environ['NEO4J_PASSWORD']))
    return driver

def run_query(url,cypherquery):
    driver = get_driver(url)
    with driver.session() as session:
        results = session.run(cypherquery)
    return list(results)

def get_chemicals(url):
    """This is all the variants.  We might want to filter on source"""
    #cquery = f'''match (a:chemical_substance) where a.smiles is not NULL and a.inchikey is not null RETURN a.inchikey, a.smiles limit 10000'''
    cquery = f'''match (a:chemical_substance) where a.smiles is not NULL and a.id is not null RETURN a.id,a.name,a.smiles limit 100'''
    records = run_query(url,cquery)
    with open('smiles.tsv','w') as outf:
        outf.write(f"id\tname\tsmiles\tcategory\n")
        #outf.write(f"Compound_name\tCASRN\tSMILES\tSolubility(µM)\tSolubility(µg/mL)\tlogSo(mol/L)\tSource\n")

        counter = 0

        for r in records:
            #print(r)
            outf.write(f'{r["a.inchikey"]}\t{r["a.name"]}\t{r["a.smiles"]}\tchemical_substance\n')
            #outf.write(f'noname\tnocasrn\t{r["a.smiles"]}\t0\t0\t0\tnosource\n')

            counter = counter + 1

            if counter > 10000:
                break;

def get_chemicals_orig(url):
    """This is all the variants.  We might want to filter on source"""
    cquery = f'''match (a:chemical_substance) where a.smiles is not NULL RETURN a.id, a.name, a.smiles limit 100'''
    records = run_query(url,cquery)
    with open('smiles.txt','w') as outf:
        for r in records:
            print(r)
            outf.write(f'{r["a.id"]}\t{r["a.name"]}\t{r["a.smiles"]}\n')


if __name__ == '__main__':
    url = 'bolt://robokopdev.renci.org:7687'
    get_chemicals_orig(url)