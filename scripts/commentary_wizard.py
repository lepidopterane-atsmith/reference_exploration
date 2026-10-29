#import codecs
import re
from dataclasses import dataclass
from lxml import etree 
from lxml.etree import DocumentInvalid, XMLSyntaxError

from pathlib import Path
from tqdm import tqdm

@dataclass
class Token:
    reference: str
    form: str =""
    lemma: str =""
    snt_id: str =""
    word_id: str =""
    postag: str =""
    head: str =""
    relation: str =""

entity_regex = re.compile(r"Entity \'(?P<entity>\w+)\' not defined")
entity_replacements = {
    'mdash': '—',
    'sect': '§'
}

cicero_work_index = cicero_list = ['Cic. S. Rosc.', 'Cic. Ver.', 'Cic. Man.', 'Cic. Catil.', 'Cic. Arch.', 'Cic. Milo.', 'Cic. Marc.', 'Cic. Lig.','Cic. Phil.', 'Other Works', 'Latin Reference']

def describe_cicero_labels(cicero_labels):
    res = []
    for label in cicero_labels:
        res.append(cicero_work_index[label-1])
    return res


# grammar_edges: 2D list of references per bin, and labels
# Returns edge tuple list fit for bipartite visualization in networkx
def bipartite_edges_from_2d_references(grammar_edges, tags):
    edges = []
    weights = []
    for i in range(len(grammar_edges)):
        value_list = []
        value_dict = dict()
        for value in grammar_edges[i]:
            src = tags[i]
            if value in value_dict:
                value_dict[value] += 1
            else:
                edges.append((src, value))
                value_list.append(value)
                value_dict[value] = 1
 
        for ii in value_list:
            weights.append(value_dict[ii])
 
    res = []
    for x in range(len(weights)):
        res.append((edges[x][0],edges[x][1],weights[x]) )
    return res

# we're sorting cicero references by where they point. 
# they can point to another cicero speech or the catch-all for not the workset itself
# really_coarse is your binning boolean. 
# returns a list networkx can use hopefully
# NOW returns a second list of every AG grammar reference in int form! list of ints!
def coarse_cicero_cleaner(reference_list, really_coarse=False):
    cicero_list = ['','Cic. S. Rosc.', 'Cic. Ver.', 'Cic. Man.', 'Cic. Catil.', 'Cic. Arch.', 'Cic. Milo.', 'Cic. Marc.', 'Cic. Lig.','Cic. Phil.']
    new_list = []
    grammar_refs = []
    for r in reference_list:
        if 'Cic.' in r:
            for c in cicero_list[1:]:
                if c in r:
                    new_list.append(cicero_list.index(c))
        elif 'AG' in r:
            new_list.append(11)
            if really_coarse:
                ref_number = int(r[3:])
                if ref_number < 50:
                    grammar_refs.append(0)
                elif ref_number < 100:
                    grammar_refs.append(50)
                else:
                    if ref_number < int(r[3]+"50"):
                        grammar_refs.append(int(r[3]+"00"))
                    else:
                        grammar_refs.append(int(r[3]+"50"))
            else:
                grammar_refs.append(int(r[3:]))
        else:
            new_list.append(10)
    return new_list, grammar_refs

# takes in a raw sequential list of textparts and returns a 2D list
# where each item has its chapter followed by its sections.
def sort_textparts(flat_textparts):
    res, current_list, first_item = [], [], True
    for textpart in flat_textparts:
        if first_item == True:
            first_item = False
        elif textpart.get('subtype') == 'chapter':
            res.append(current_list)
            current_list = []
        current_list.append(textpart)
    res.append(current_list)
    return res

# returns basic counter of how many elements in each section textpart (section_elements_list) 
# along with lemma count (lemmata_per_elements) and ref count (refs_per_elements) by same index
# does not separate by chapter, though we can always change that
def count_section_elements(textpart_list):
    section_elements_list, lemmata_per_elements, refs_per_elements = [], [], []
    for t in textpart_list:
        if t.get('subtype') != 'chapter':
             #, etree.tostring(t))
            section_elements, lemmata, refs = 0, 0, 0
            for s in t:
                section_elements += len(s) + 1
                s_string = str(etree.tostring(s))
                lemmata = sum([1 for i in s_string.split('<') if "/lem" in i])
                refs = sum([1 for i in s_string.split('<') if "/bibl" in i])
                #print([i for i in s_string.split('<') if "bibl" in i])
            section_elements_list.append(section_elements)
            lemmata_per_elements.append(lemmata)
            refs_per_elements.append(refs)
        # else:
        #    print(t.get('corresp'), t.get('n'))
    return section_elements_list, lemmata_per_elements, refs_per_elements

# how do I actually make this parse
def parse_doc(filename):
    try:
        doc = etree.parse(filename)
        root = doc.getroot()
        
        lemma_words = ""
        lemma_space = " "

        for lemon in root.findall(".//{http://www.tei-c.org/ns/1.0}lem"):
            lemma_words = lemma_words + lemma_space + str(lemon.text)

        #print(len(lemma_words.replace('.',' ').replace(',',' ').split()), "hi")
        return root

    except XMLSyntaxError as e:
        msg = e.msg
        entity_match = entity_regex.search(msg)
        
        print("two")

        if entity_match is not None:
            print("three")
            entity = entity_match.group('entity')
            replacement = entity_replacements[entity]
            print(f"Replacing {entity} with {replacement} in {filename}")
            
            with open(filename, 'r') as f:
                filedata = f.read()
            
            fixed = filedata.replace(f'&{entity};', replacement)

            with open(filename, 'w') as f:
                f.write(fixed)

            return parse_doc(filename)
        else: 
            print(e)


# blah = parse_doc("data/sec00009/sec002/sec00009.sec002.perseus-eng1.xml")
#gorman_tokens.extend(get_gorman_tokens("thuc-1-121-146-bu3.xml"))
# ^ if looking at a sample not captured fully in one of these gormans, this is what I do