"""
This library's job is to find the closest bible book based on provided text
It does this using fuzzy pattern matching
NOTE: python whimpers that the fuzzywuzzy library would be faster if python-Levenshtein were installed
However, python-Levenshtein relies upon pylcs which has been an unusually tricky dependency to manage.
This thing is intended to run in a lambda- who cares if you have to spin up a few more.
"""


#~IMPORT~LIBRARIES~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from fuzzywuzzy import fuzz # See note above
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


def closest_bible_book(title,verbose=False):
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


def extract_bible_refs(text):
    # given a body of text, extract bible references and harmonize them
    refs = scriptures.extract(text.replace('.',' ')) # otherwise it recognizes Rev but not Rev.
    return [ harmonize_bible_ref(ref) for ref in refs ]


#~~~TESTS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_books():
    assert( closest_bible_book("Gen") == "Genesis" )
    assert( closest_bible_book("II Sam") == "2 Samuel")
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~