"""
This library's job is to find the closest bible book based on provided text
It does this using fuzzy pattern matching
NOTE: python whimpers that the fuzzywuzzy library would be faster if python-Levenshtein were installed
However, python-Levenshtein relies upon pylcs which has been an unusually tricky dependency to manage.
This thing is intended to run in a lambda- who cares if you have to spin up a few more.
"""


#~IMPORT~LIBRARIES~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from typing import List, Optional, Tuple
from fuzzywuzzy import fuzz # See note above
import number_parser # for converting 'second' to '2' etc.
import scriptures   # for parsing bible verses
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


bible_order = ['Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
    'Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel',
    '1 Kings', '2 Kings','1 Chronicles', '2 Chronicles',
    'Ezra', 'Nehemiah', 'Esther', 'Job', 'Psalms',
    'Proverbs', 'Ecclesiastes', 'Song of Solomon',
    'Isaiah', 'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel',
    'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah', 'Micah', 'Nahum',
    'Habakkuk', 'Zephaniah', 'Haggai','Zechariah', 'Malachi',
    'Matthew', 'Mark', 'Luke', 'John',
    'Acts', 'Romans', '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians',
    'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians',
    '1 Timothy', '2 Timothy', 'Titus', 'Philemon', 'Hebrews', 'James',
    '1 Peter', '2 Peter', '1 John', '2 John', '3 John', 'Jude', 'Revelation']


def closest_bible_book(title: str,verbose=False):
    # This function matches 'Song of Songs' to 'Song of Solomon' etc.
    original = title
    best_match = '', 0
    title = title.replace('II ','2 ').replace('I ','1 ').replace(' Songs',' Solomon')
    for x in ['1','2','3']:
        if title.startswith(x) and not title.startswith(x+' '):
            title = title.replace(x,x+' ')
    if title == 'Ps':
        title = 'Psalms'
    for book in bible_order:
        fr = fuzz.ratio(title,book)
        if fr > best_match[1] and title.lower()[:3] == book.lower()[:3]:
            best_match = book, fr
    if verbose:
        print(original,'  matched to ',best_match[0])
    return best_match[0]


def harmonize_bible_ref(bible_ref):
    # ensure the book matches the agreed primary key
    book = bible_ref[0]
    book = closest_bible_book(book)
    new_ref = list(bible_ref) # tuples are not mutable
    new_ref[0] = book
    underscore_book = book.replace(' ','_') # this is needed for replacements
    new_ref.append(underscore_book)
    return tuple(new_ref)


def text_to_numbers(text: str):
    ''' convert numbers as text to numbers. Also, insert a ":" (denoting a verse)
    between subsequent numbers. This is done so that if you are looking for passages 
    in a transcript of a sermon like "Genesis twenty two seventeen", you can 
    preprocess the text to "Genesis 22:17" etc. '''
    # 1) convert words to numbers
    text = number_parser.parse(text)
    # loop through all the words. If two consecutive ones are numbers, insert a ":"
    old_words, new_words, prior_is_numeric = text.split(), [], False
    for word in old_words:
        word_is_numeric = word.isnumeric()
        if (prior_is_numeric and word_is_numeric):
            new_words.append(":")
        new_words.append(word)
        prior_is_numeric = word_is_numeric
    text =  ' '.join(new_words)
    # Because it has over 100 chapters, psalms is an odd case
    # Consider "Psalm one o eight" or "Psalm one twenty"
    text = text.replace('Psalm', 'psalm')
    text = text.replace('psalm one o ', 'psalm 100')
    text = text.replace('psalm 1 : ', 'psalm 1')
    return text


# this dictionary represents a list of word replacements
# when parsing speech if the following word is numeric 
speech_pre_numeric_reps = {
    'chapter':None, 'chapters':None, 'in':None, 'starting':None, 'at':None,
    'verse':':', 'verses':':',
    'thru':'-', 'through':'-', 'to':'-', 'and':'-'
}

def is_a_number(word: str):
    # this is like .isnumeric(), but allows punctuation at the end of a number.
    for char in '.?!':
        if word.endswith(char):
            word = word.replace(char, '')
    return word.isnumeric()

def _sub_pre_numeric_words(old_words: List[str]) -> List[str]:
    # Make pre-numeric substitutions so 'Chapter 2' becomes '2' etc.
    old_words += ['|'] # this never gets appended because you stop one from the end, but it lets you evaluate the prior word
    new_words = []
    for i in range(0,len(old_words)-1):
        word, next_word = old_words[i], old_words[i+1]
        if (is_a_number(next_word) or next_word == ':'):
            word = speech_pre_numeric_reps.get(word.lower(), word)
            if word: # this will skip if the replacement value is None
                new_words.append(word)
        else:
            new_words.append(word)
    return new_words 

def speech_preprocess(text: str) -> str:
    ''' This function should be used to preprocess text that came from a transcript:
    I.e. a sermon or other speech. This converts things like "Genesis twenty two two thru five" to "Genesis 22 : 2 - 5"
    This is the second most important function in this library, after extract_bible_refs '''
    text = text_to_numbers(text)
    words = text.split()
    words = _sub_pre_numeric_words(words)
    words = _sub_pre_numeric_words(words) # sub again so 'in verse 2' becomes '2'
    words = _sub_pre_numeric_words(words) # sub again so 'starting in verse 2' becomes '2'
    return ' '.join(words)


def _extract_bible_refs(text: str) -> List[Tuple[object]]:
    # given a body of text, extract bible references and harmonize them
    refs = scriptures.extract(text.replace('.',' ')) # otherwise it recognizes Rev but not Rev.
    return [ harmonize_bible_ref(ref) for ref in refs ]


def nullify_unspecified_verses(ref):
    # if a reference is to a whole chapter(s), set the verses to null
    book, start_chap, start_verse, end_chap, end_verse, _name = ref
    if start_chap == end_chap:
        test_text = '{} {}'.format(book, start_chap) # i.e. 'Exodus 2'
    else:
        test_text = '{} {} - {}'.format(book, start_chap, end_chap) # i.e. 'Exodus 2 - 3'
    # try parsing the reference again without reference to verses 
    test_ref = _extract_bible_refs(test_text)[0]
    _, _, test_start_verse, _, test_end_verse, _ = test_ref 
    if (start_verse == test_start_verse) and (end_verse == test_end_verse):
        start_verse, end_verse = None, None 
    return book, start_chap, start_verse, end_chap, end_verse, _name 


def extract_bible_refs(text: str, preprocess: Optional[bool]=False, nullify: Optional[bool]=True) -> List[Tuple[object]]:
    '''
    This is the main function for which this library exists.
    Given a body of text, extract any bible references.
    ARGUMENTS:
    text: the passage in which you want to search for references, i.e. "I read 2 Kings 22:2 today"
    preprocess: preprcess text for use with transcribed speech.
        Set this to True for things like "I read second kings twenty two two today"
    nullify: set this to True so that verse references are null when the reference is to an entire chapter(s)
        If this is set to false, the starting and ending verses of the chapter will be set.
    '''
    preprocessed_text = None
    if preprocess:
        preprocessed_text = speech_preprocess(text)
        text = preprocessed_text
    refs = _extract_bible_refs(text)
    if nullify:
        refs = [ nullify_unspecified_verses(ref) for ref in refs ]
    return preprocessed_text, refs




#~~~TESTS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_closest_books():
    # Ensure you can harmonize bible books 
    assert( closest_bible_book("Gen") == "Genesis" )
    assert( closest_bible_book("II Sam") == "2 Samuel")

def test_text_to_numbers():
    # test the text_to_numbers function 
    # note the sepcial attention to Psalms
    assert text_to_numbers('I ate one hundred seventy five apples last year') == 'I ate 175 apples last year'
    assert text_to_numbers('psalm one forty three') == 'psalm 143'
    assert text_to_numbers('psalm one seventeen eleven') == 'psalm 117 : 11'
    assert text_to_numbers('Today I read psalm one forty five six and revelation twenty two two') == 'Today I read psalm 145 : 6 and revelation 22 : 2'

def test_speech_preprocess():
    # ensure you can perform substitutions to replace speech transcripts with text
    # more easily recongizable by the scriptures module 
    # some of these examples were taken from actual YouTube video transcripts 
    assert speech_preprocess('I read Psalm one eighteen starting in verse eight thru  twelve') == 'I read psalm 118 : 8 - 12'
    assert speech_preprocess(' if you go back to Genesis chapter 4 to') == 'if you go back to Genesis 4 to'
    assert speech_preprocess('things Isaiah 51 verse 1 and 2 listen') == 'things Isaiah 51 : 1 - 2 listen'

def test_extract_1():
    x1 = extract_bible_refs('Yesterday I read Psalm one eleven five to eight slowly', preprocess=True, nullify=True)
    assert x1 == ('Yesterday I read psalm 111 : 5 - 8 slowly', [('Psalms', 111, 5, 111, 8, 'Psalms')])
    x2 = extract_bible_refs('Yesterday I read Psalm one eleven quickly', preprocess=True, nullify=True)
    assert x2 == ('Yesterday I read psalm 111 quickly', [('Psalms', 111, None, 111, None, 'Psalms')])

def test_exract_2():
    x1 = extract_bible_refs('Today Samuel read Second samuel  five.', preprocess=True, nullify=True)
    assert x1 == ('Today Samuel read 2 samuel 5.', [('2 Samuel', 5, None, 5, None, '2_Samuel')])
    x2 = extract_bible_refs('Today Samuel read Second samuel chapter five.', preprocess=True, nullify=True)
    assert x2 == ('Today Samuel read 2 samuel 5.', [('2 Samuel', 5, None, 5, None, '2_Samuel')])
    x3 = extract_bible_refs('Today Samuel read Second samuel five  eight thru twenty one.', preprocess=True, nullify=True)
    assert x3 == ('Today Samuel read 2 samuel 5 : 8 - 21.', [('2 Samuel', 5, 8, 5, 21, '2_Samuel')])
    x4 = extract_bible_refs('Today Samuel read Second samuel chapter five  eight thru twenty one.', preprocess=True, nullify=True)
    assert x4 == ('Today Samuel read 2 samuel 5 : 8 - 21.', [('2 Samuel', 5, 8, 5, 21, '2_Samuel')])
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~