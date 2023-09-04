""" This file is intended to
1) Take a body of text as input
2) Find all the references to Bible passages in the text
3) Find all the Named Entities in the text
4) Return the text formatted with <a href> links, a list of bible refs, and a list of entities
NOTE: For reasons not fully understood, Spacy Named Entity Recognition works reliably in python 3.8xx, 
but has been problematic in python 3.10xx. 
"""

#~IMPORT~LIBRARIES~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import spacy        # for NLP
from collections import namedtuple
from random import choice
from string import ascii_lowercase
# Locally defined stuff
from closest_bible_book import extract_bible_refs
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



#~~~Initialization~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Characters
cc = 'abcdefghijklmnopqrstuvwxyz '

# common_words
try:
    # first try this for local development
    with open('layers/common_words.txt', 'r') as h:
        common_words = h.read().split('\n')
except:
    # Then try here for use on a Lambda
    with open('/opt/common_words.txt', 'r') as h:
        common_words = h.read().split('\n')
common_words = set([ word.strip() for word in common_words ])
for word in 'yea ye thou behold'.split():
    common_words.add(word)

# spacy lamguage model
try:
    # use this import for local development
    nlp = spacy.load('en_core_web_sm')
except:
    # use this import from AWS Lambda
    nlp = spacy.load("/opt/en_core_web_sm/en_core_web_sm-2.3.1")
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~~~HTML~Templates~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
link_template_entity = """<a href='javascript:void' onclick='clickNamedEnt("{}")'> {} </a>"""
link_template_bible = """<a href='javascript:void' onclick='clickPassage("bible", "{}", "{}", {}, "{}", {}, "{}")'> {} </a>"""
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~~~NLP:~Extracting~Named~Entities~~~~~~~~~~~~~~~~~~~~~~~
EntTup = namedtuple("EntTup", "key name pos")

def spacy_to_ent_tup(spacy_ent):
    # Given a named entity from spacy, convert it to an EntTup
    name, pos = spacy_ent.text, spacy_ent.label_
    pos = {'PERSON': 'PER'}.get(pos, pos) # to fit CHAR(3) type
    if not name[-1].isalpha():
        name = name[:-1]
    key = name.replace(' ','_').lower()
    return EntTup(key, name, pos)


def is_each_word_capitalized(phrase):
    # return True if each word in a phrase is capitalized
    sp = phrase.split()
    non_caps = [ 0 if word[0].isupper() else 1 for word in sp ]
    return sum(non_caps) == 0


def phrase_has_clean_chars(phrase):
    # return True if none of the characters in a phrase are weird #$!@>
    bad_chars = [ 0 if char.lower() in cc else 1 for char in phrase ]
    return sum(bad_chars) == 0


def extract_named_entities(text):
    # given text, extract a list of named entities as EntTup
    doc = nlp(text)
    entities = [ spacy_to_ent_tup(spacy_ent) for spacy_ent in doc.ents  ]
    # filter out funky parts of speech
    entities = [ ent for ent in entities if ent.pos in ('GPE', 'ORG', 'PER')]
    # filter out common words
    entities = [ ent for ent in entities if not ent.name.lower() in common_words]
    # filter out things that aren't capitalized
    entities = [ ent for ent in entities if is_each_word_capitalized(ent.name)]
    # filter out entities with funky characters
    entities = [ ent for ent in entities if phrase_has_clean_chars(ent.name)]
    # filter out very long names per VARCHAR(63) limitation
    entities = [ ent for ent in entities if ( len(ent.name) < 50 )]
    return entities


def add_entities(text):
    # Given a body of text, find entities with NLP.
    # Highlight them with html and return a list of entities
    entities = extract_named_entities(text)
    # shor tthem from longest to smallest
    sort_ents = sorted(list(set(entities)), key=lambda x:-len(x.name))
    ents_as_dicts = []
    # replace ents in text with hyml hyperlinks
    html = text
    for ent in sort_ents:
        html = html.replace(ent.name, link_template_entity.format( ent.key, ent.name))
        ents_as_dicts.append( dict(ent._asdict()) ) # for JSON serializatin
    return html, entities, ents_as_dicts # return both formats
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~~~Extracting~Bible~References~~~~~~~~~~~~~~~~~~~~~~~~~~



def chap_no(chap_verse):
    # return the chapter from possible references to chapter and verse
    chap = chap_verse.replace('-',':').split(':')[0].strip()
    return chap


def alphaword(word):
    # return just the letters from a word- no punctuation
    word = word.lower()
    return ''.join([ char for char in word if char in 'abcdefghijklmnopqrstuvwxyz_1234567890' ])


def numeric_content(string):
    return ''.join([ char for char in string if char in '1234567890:-' ])


def is_chapter_verse_ref(chap_verse):
    # return True for anything that looks like  chapter/verse
    for char in '-:.,()!?':
        chap_verse = chap_verse.replace(char, '')
    return chap_verse.isnumeric()


def replace_multiword_books(text, refs):
    # given text and the bible references therein
    sp = text.split()
    for ref in refs:
        uRef = ref[-1] # consider the underscore version of the name
        if not '_' in uRef:
            continue # no need to do replacements on Exodus, Matthew, etc.
        for i in range(0, len(sp)- 2):
            phrase = '{} {}'.format(sp[i], sp[i+1]) # Note this will not 'catch' "1\nPeter Rabbit"
            uPhrase = phrase.replace(' ','_')
            if uPhrase.lower()[:5] == uRef.lower()[:5]: # i.e the match "1_Peter" to "1 pEt"
                text = text.replace(phrase, uRef)
    return text


def add_bible_ref_placeholders(text):
    # replace extra spaces but not newlines
    for _ in range(0,3):
        text = text.replace('  ',' ')
    refs = extract_bible_refs(text)
    text = replace_multiword_books(text, refs)
    #print(refs)
    replacements = []
    named_bible_refs = []
    placeholders = {}
    placeholderNo = 0
    ref_index = 0
    if refs == []:
        # No bible references were found
        return text, placeholders, named_bible_refs
    ref = refs[ref_index]
    #print('Looing for ref', ref)
    words = text.replace('\n',' | ').split()
    for start_index in range(0, len(words)-1):
        word = words[start_index]
        #print('  At',word)
        if ref[5].lower().startswith(alphaword(word)): # ref[5] = underscore book name
            #print('    testing', word)
            #print('    NEXT',words[start_index + 1],">",chap_no(numeric_content(words[start_index + 1])))
            if chap_no(numeric_content(words[start_index + 1])) == str(ref[1]):
                replace_text = words[start_index:start_index+2]
                if start_index +2 <= len(words) - 1: # don't go past the last word
                    #print('maybe add', words[start_index+2])
                    # you only have the book and the (starting) chapter so far. What if there is a verse or another chapter?
                    if is_chapter_verse_ref(words[start_index+2]):
                        replace_text = words[start_index:start_index+3]
                    elif (words[start_index+2] == '-') and (start_index +2 <= len(words) - 1):
                        # capture things like Exodus 12:2 - 13:5
                        if is_chapter_verse_ref(words[start_index+3]):
                            replace_text = words[start_index:start_index+4]
                replacements.append([' '.join(replace_text), ref])
                #print(replace_text,"=",ref)
                # move on to the next reference
                ref_index += 1
                try:
                    ref = refs[ref_index]
                except:
                    break # you presumably reached the last reference
    # sort the replacements by longest string first
    # this is so you replace ('Isaiah 22 : 4' before 'Isaiah 22')
    sorted_replacements = sorted(replacements, key=lambda x: -len(x[0]))
    for origText, ref in sorted_replacements:
        if origText[-1] in ('.,!?'):
            origText = origText[:-1]
        book, fromChap, fromVerse, toChap, toVerse, _ = ref
        # convert Rev. 22 to Revelation 22 etc. for the passage name
        passageName = origText.replace(': ',':').split()
        passageName = [book] + [ numeric_content(x) for x in passageName[1:] ]
        passageName = ' '.join(passageName)
        named_bible_refs.append([book, fromChap, fromVerse, toChap, toVerse, passageName])
        placeholderNo+=1
        placeholderKey = 'xref_bible_{}'.format(str(placeholderNo).zfill(4))
        placeholders[placeholderKey] = [book, fromChap, fromVerse, toChap, toVerse, origText, passageName]
        text = text.replace(origText, placeholderKey)
    return text, placeholders, named_bible_refs


def sub_bible_placeholders(text, placeholders):
    # given text with placeholders from add_bible_ref_placeholders, replace those placeholders
    words = text.split()
    for word in words:
        if not word.startswith('xref_bible_'):
            continue
        if word[-1] in '.,!?;':
            word = word[:-1]
        if not word in placeholders:
            print('??? How a word that didn\'t belong in there?')
            continue # This happens on rare occasions
        book, fromChap, fromVerse, toChap, toVerse, origText, passageName = placeholders[word]
        #"""<a href='javascript:void' onclick='clickPassage("bible", "{}", "{}", {}, "{}", {}, "{}")'> {} </a>"""
        repHTML = link_template_bible .format(book, fromChap, fromVerse, toChap, toVerse, passageName, origText)
        text = text.replace(word, repHTML)
    return text
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~~~COMBINED~BIBLE~&~NAMED~ENTITY~RECOGNITION~~~~~~~~~~~~
def enrich(text):
    # look for bible passages and named entities in text and enrich it
    # The first part of the output is JSON-serializable for http.
    # the second part (list of EntTup namedtuples ) is for internal use
    text, placeholders, named_bible_refs = add_bible_ref_placeholders(text)
    text, entities, ents_as_dicts = add_entities(text)
    text = sub_bible_placeholders(text, placeholders)
    return {'html':text, 'named_bible_refs':named_bible_refs, 'entities':ents_as_dicts}, entities
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~~~TESTS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_enrich_simple():
    # perform enrichment on a simple passage and and test the results
    text = 'Let\'s visit Coffee Shop Bleu and study Exodus 22.'
    data, _ = enrich(text)
    assert data['html'] == 'Let\'s visit <a href=\'javascript:void\' onclick=\'clickNamedEnt("coffee_shop_bleu")\'> Coffee Shop Bleu </a> and study <a href=\'javascript:void\' onclick=\'clickPassage("bible", "Exodus", "22", 1, "22", 31, "Exodus 22")\'> Exodus 22 </a>.'
    assert data['named_bible_refs'] == [['Exodus', 22, 1, 22, 31, 'Exodus 22']]
    assert data['entities'] == [{'key':'coffee_shop_bleu', 'pos':'ORG', 'name':'Coffee Shop Bleu'}]


def test_multichapter_bible_refs():
    # try to extract multi-chapter bible refs
    text = '''I read my favorite passage (Galatians 3) yesterday.\n\nIt reminds be of Rev. 22: 4-5 (also Exodus 12:3 - 14:8) which is cool.'''
    ans = add_bible_ref_placeholders(text)
    expected_sub = '''I read my favorite passage xref_bible_0002 yesterday.\n\nIt reminds be of xref_bible_0003 (also xref_bible_0001 which is cool.'''
    assert ans[0] == expected_sub
    assert ans[1] == {
        'xref_bible_0001': ['Exodus', 12, 3, 14, 8, 'Exodus 12:3 - 14:8)', 'Exodus 12:3 - 14:8'],
        'xref_bible_0002': ['Galatians', 3, 1, 3, 29, '(Galatians 3)', 'Galatians 3'],
        'xref_bible_0003': ['Revelation', 22, 4, 22, 5, 'Rev. 22: 4-5', 'Revelation 22:4-5']}
    assert ans[2] == [
        ['Exodus', 12, 3, 14, 8, 'Exodus 12:3 - 14:8'],
        ['Galatians', 3, 1, 3, 29, 'Galatians 3'],
        ['Revelation', 22, 4, 22, 5, 'Revelation 22:4-5']]


def test_replace_multiword_books():
    # Test the function replace_multiword_books
    text = '1 john 3 is a favourite passage'
    refs = [('1 John', 3, 1, 3, 24, '1_John')]
    res = replace_multiword_books(text, refs)
    assert res == '1_John 3 is a favourite passage'


def test_multiword_refs():
    # test the capture of references to multiword bible books
    resp = add_bible_ref_placeholders('today I read 1 John 2- it is my favorite')
    assert resp == (
        'today I read xref_bible_0001 it is my favorite',
        {'xref_bible_0001': ['1 John', 2, 1, 2, 29, '1_John 2-', '1 John 2-']},
        [['1 John', 2, 1, 2, 29, '1 John 2-']]
    )
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
