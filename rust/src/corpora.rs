use std::error::Error;
use std::fmt;  
use serde::{Serialize, Deserialize};
use tokio_postgres::{Row};

use pachydurable::{err::{DiskError}, connect::ClientNoTLS,  redis::Cacheable};


/// There are only a few copora so they can be enumerated
#[derive(Serialize, Deserialize, Debug)]
pub enum Corpus {
    Bible, 
    Talmud,
    Josephus,
    Enoch,
}


impl Corpus {
    pub fn default_translation(&self) -> (i16, Translation) {
        match *self {
            Corpus::Bible => (1i16, Translation::Lexham),
            Corpus::Talmud => (2i16, Translation::EnglishSefaria),
            Corpus::Josephus => (-99i16, Translation::EnglishSefaria), // trans_id TBD
            Corpus::Enoch => (-99i16, Translation::EnglishEnoch), // trans_id TBD
        }
    }
    pub fn from_name(corpus_name: &str) -> Result<Self, CorpusError> {
        match corpus_name.to_lowercase().as_ref() {
            "bible" => Ok(Corpus::Bible),
            "talmud" => Ok(Corpus::Talmud),
            "josephus" => Ok(Corpus::Josephus),
            "enoch" => Ok(Corpus::Enoch),
            _ => Err(CorpusError{msg: format!("unable to decipher corpus '{}'", corpus_name)}),
        }
    }
}

/// There are only a few translations so they can be enumerated
#[derive(Serialize, Deserialize, Debug)]
pub enum Translation {
    KingJamesVersion,
    Lexham,
    Hebrew,
    EnglishSefaria,
    EnglishEnoch,
}
/*impl Translation {
    pub fn from_name(trans_name: &str) -> Result<Self, CorpusError> {
        match trans_name.to_lowercase().as_ref() {
            "king james" => Ok(Translation::KingJames),
            "lexham" => Ok(Translation::Lexham),
            "hebrew" => Ok(Translation::Hebrew),
            "english" => Ok(Translation::English),
            _ => Err(CorpusError{msg: format!("unable to decipher translation '{}'", trans_name)}),
        }
    }
}*/

/// A Book (i.e. Genesis, Bava Batra, etc.) has a corpus, a unique book_id, and a name
#[derive(Serialize, Deserialize, Debug)]
pub struct Book {
    pub corpus: Corpus,
    pub book_id: i16,
    pub name: String,
}

/// The Verse struct (separate from the VerseText) struct is intended to send all the information about one verse
/// so it can be read/viewed. This may come up often in the context of searching
#[derive(Serialize, Deserialize, Debug)]
pub struct Verse {
    pub book: Book,
    pub translation: Translation,
    pub chap_no: String,
    pub verse_no: i16,
    pub text: String,
    pub html: String,
    pub ct_ref_verse: i32,  // count of inbound references from verses mentioning this verse
    pub ct_ref_npara: i32,  // count of inbound references from note paragraphs mentioning this verse
    pub ct_ref_vpara: i32,  // count of inbound references from videos mentioning this verse
}


impl<'a> tokio_postgres::types::FromSql<'a> for Verse {
    fn from_sql(_ty: &tokio_postgres::types::Type, raw: &'a [u8]) -> Result<Self, Box<dyn std::error::Error + Sync + Send>> {
        let verse: Verse = serde_json::from_slice(raw)?;
        Ok(verse)
    }
    fn accepts(_ty: &tokio_postgres::types::Type) -> bool {
        true
    }
}


/// The Chapter struct is intended for sending all the information about a chapter so it can be read
#[derive(Serialize, Deserialize, Debug)]
pub struct Chapter {
    pub name: String,       // i.e. "Genesis 22" etc.
    pub ct_ref_verse: i32,  // count of inbound references from verses mentioning 1+ verses in this chapter
    pub ct_ref_npara: i32,  // count of inbound references from note paragraphs mentioning 1+ verses in this chapter
    pub ct_ref_vpara: i32,  // count of inbound references from videos mentioning 1+ verses in this chapter
    pub verses: Vec<Verse>,
}



impl<'a> tokio_postgres::types::FromSql<'a> for Chapter {
    fn from_sql(_ty: &tokio_postgres::types::Type, raw: &'a [u8]) -> Result<Self, Box<dyn std::error::Error + Sync + Send>> {
        let chapter: Chapter = serde_json::from_slice(raw)?;
        Ok(chapter)
    }
    fn accepts(_ty: &tokio_postgres::types::Type) -> bool {
        true
    }
}


/// A TorahPortion is similar to a passage, but it conains multiple chapters
/// Note that some chapters may be "cut short" depending on where the passage starts & stops
#[derive(Serialize, Debug)]
pub struct TorahPortion {
    pub name: String,   // the name of the Torah Portion
    pub location: String, // i.e. Exodus 1:1 - 5:10 or whatever
    pub torah: Vec<Chapter>,     // partial chapters are okay
}




impl Cacheable for Verse {
    fn query() ->  &'static str {
        "SELECT verse FROM verse_struct WHERE book = $1 AND chapter_no = $2 AND verse_no = $3 AND trans_id = $4"
    }

    fn from_row(row: &Row) -> Self {
        let verse: Verse = row.get(0);
        verse
    }

    fn key_prefix() ->  &'static str {
        "verse"
    }

    fn seconds_expiry() -> usize {
        86_400usize // one day
    }
}


#[derive(Debug)]
pub struct CorpusError {
    pub msg: String
}

impl Error for CorpusError {
    fn description(&self) -> &str {
        &self.msg
    }
}

impl fmt::Display for CorpusError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f,"CorpusError: {}",self.msg)
    }
} 
