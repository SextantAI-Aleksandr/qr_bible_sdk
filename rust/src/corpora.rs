//! This module contains core structs such as Verses and Chapters associated with corproa.
//! By factoring out these structs from the backend service creating them,
//! Users can create clients that are prepared to deserialize those same structs for 
//! ther own application. 


use std::{error::Error, fmt, vec::Vec};
use serde::{Serialize, Deserialize};
use tokio_postgres::Row;
use pachydurable::redis::Cacheable;


/// There are only a few copora so they can be enumerated
#[derive(Serialize, Deserialize, Debug)]
pub enum Corpus {
    Bible, 
    Talmud,
    Josephus,
    Enoch,
    Apocrypha
}


impl Corpus {
    pub fn from_name(corpus_name: &str) -> Result<Self, CorpusError> {
        match corpus_name.to_lowercase().as_ref() {
            "bible" => Ok(Corpus::Bible),
            "talmud" => Ok(Corpus::Talmud),
            "josephus" => Ok(Corpus::Josephus),
            "enoch" => Ok(Corpus::Enoch),
            "apocrypha" => Ok(Corpus::Apocrypha), 
            _ => Err(CorpusError{msg: format!("unable to decipher corpus '{}'", corpus_name)}),
        }
    }
}


/// The translation struct captures that there will often be more than one translation for a given passage
#[derive(Serialize, Deserialize, Debug)]
pub struct Translation {
    /// a unique ID for this translation
    pub trans_id: i16,
    /// the name of this translation, 
    pub translation: String,
}

/// The TransData struct captures both the selected translation as well as the available translations for a passage
#[derive(Serialize, Deserialize, Debug)]
pub struct TransData {
    /// The currently selected translation
    pub selected: Translation,
    /// A footnote to display about the translation and associated license
    pub footnote: String,
    /// A url to more information about the translation
    pub url: String,
    /// A list of all available translations for the given passage
    pub available: Vec<Translation>
}

/// The Passage generic allows you to remove translation data from chater and verse structs
/// This is useful since the Chapter struct contains the Verse struct, but providing TransData
/// along with each and every verse is very inefficient
#[derive(Serialize, Deserialize, Debug)]
pub struct Passage<T> {
    pub pass: T,
    pub translations: TransData,
}

/// A Book (i.e. Genesis, Bava Batra, etc.) has a corpus, a unique book_id, and a name
#[derive(Serialize, Deserialize, Debug)]
pub struct Book {
    pub corpus: Corpus,
    pub book_id: i16,
    pub name: String,
}

/// This struct counts cross-references, both explicit and based on topic (semantic) similarity 
/// for ONE source
#[derive(Serialize, Deserialize, Debug)]
pub struct XrefSrcCt {
    /// count of "eXplicit References" - where a passage is named
    pub xpl_ref: i32,
    /// count of "Similar Topics" - where semantic similarity is high 
    pub sim_top: i32,
}

/// this struct summarizes Cross-References by source 
#[derive(Serialize, Deserialize, Debug)] 
pub struct XrefCt {
    /// references from other passages (bible, talmud, etc.)
    pub passages: XrefSrcCt,
    /// references from notes
    pub notes: XrefSrcCt,
    /// references from youtube videos
    pub videos: XrefSrcCt,
}


/// The Verse struct (separate from the VerseText) struct is intended to send all the information about one verse
/// so it can be read/viewed. This may come up often in the context of searching
#[derive(Serialize, Deserialize, Debug)]
pub struct Verse {
    pub name: String,       // i.e. "Genesis 22:2" etc.
    pub book: Book,
    pub chapter_no: String,
    pub verse_no: i16,
    pub text: String,
    pub html: String,
    /// count of cross-references by source
    pub xref_ct: XrefCt
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
    pub book: Book,
    pub chapter_no: String,
    /// count of cross-references by source
    pub xref_ct: XrefCt,
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

#[derive(Serialize, Deserialize, Debug)]
pub struct TorahPortion {
    /// The id for this torah portion 
    pub portion_id: i16, 
    /// The name of the Torah Portion, i.e. 'Shemot' or 'Haazinu'
    pub name: String,
    /// the location of the portion, i.e. 'Exodus 1:1 - 5:10' etc. 
    pub location: String, // i.e. Exodus 1:1 - 5:10 or whatever
    /// A vec of chapter structs, where some chapters may not contain the full set of verses
    pub chapters: Vec<Chapter>,
}


impl<'a> tokio_postgres::types::FromSql<'a> for TorahPortion {
    fn from_sql(_ty: &tokio_postgres::types::Type, raw: &'a [u8]) -> Result<Self, Box<dyn std::error::Error + Sync + Send>> {
        let torah_portion: TorahPortion = serde_json::from_slice(raw)?;
        Ok(torah_portion)
    }
    fn accepts(_ty: &tokio_postgres::types::Type) -> bool {
        true
    }
}

impl<'a> tokio_postgres::types::FromSql<'a> for Translation {
    fn from_sql(_ty: &tokio_postgres::types::Type, raw: &'a [u8]) -> Result<Self, Box<dyn std::error::Error + Sync + Send>> {
        let trans: Translation = serde_json::from_slice(raw)?;
        Ok(trans)
    }
    fn accepts(_ty: &tokio_postgres::types::Type) -> bool {
        true
    }
}




impl Cacheable for Passage<Verse> {
    fn query() ->  &'static str {
        "SELECT vs.verse, t.trans_id, t.translation, t.footnote, t.url, tjz.available_trans
        FROM verse_struct vs 
        INNER JOIN translations t ON vs.trans_id = t.trans_id 
        INNER JOIN translations_jz tjz ON vs.book_id = tjz.book_id 
        WHERE vs.book = $1 AND vs.chapter_no = $2 AND vs.verse_no = $3 AND vs.trans_id = $4"
    }

    fn from_row(row: &Row) -> Self {
        let verse: Verse = row.get(0);
        let trans_id: i16 = row.get(1);
        let translation: String = row.get(2);
        let footnote: String = row.get(3);
        let url: String = row.get(4);
        let selected = Translation{trans_id, translation};
        let available: Vec<Translation> = row.get(5);
        Passage{pass: verse, translations: TransData{selected, footnote, url, available}}
    }

    fn key_prefix() ->  &'static str {
        "verse"
    }

    fn seconds_expiry() -> usize {
        86_400usize // one day
    }
}


impl Cacheable for Passage<Chapter> {
    fn query() ->  &'static str {
        "SELECT ch.chapter, t.trans_id, t.translation, t.footnote, t.url, tjz.available_trans
        FROM chapter_struct ch 
        INNER JOIN translations t ON ch.trans_id = t.trans_id 
        INNER JOIN translations_jz tjz ON ch.book_id = tjz.book_id 
        WHERE ch.book = $1 AND ch.chapter_no = $2 AND ch.trans_id = $3 "
    }

    fn from_row(row: &Row) -> Self {
        let chapter: Chapter = row.get(0);
        let trans_id: i16 = row.get(1);
        let translation: String = row.get(2);
        let footnote: String = row.get(3);
        let url: String = row.get(4);
        let selected = Translation{trans_id, translation};
        let available: Vec<Translation> = row.get(5);
        Passage{pass: chapter, translations: TransData{selected, footnote, url, available}}
    }

    fn key_prefix() ->  &'static str {
        "chapter"
    }

    fn seconds_expiry() -> usize {
        86_400usize // one day
    }
}


impl Cacheable for Passage<TorahPortion> {
    fn query() ->  &'static str {
        "SELECT torah_portion, t.trans_id, t.translation, t.footnote, t.url, tjz.available_trans
        FROM torah_portion_struct tps
        INNER JOIN translations t ON tps.trans_id = t.trans_id 
        INNER JOIN translations_jz tjz ON tps.book_id = tjz.book_id 
        WHERE tps.portion_id = $1 AND tps.trans_id = $2"
    }

    fn from_row(row: &Row) -> Self {
        let torah_portion: TorahPortion = row.get(0);
        let trans_id: i16 = row.get(1);
        let translation: String = row.get(2);
        let footnote: String = row.get(3);
        let url: String = row.get(4);
        let selected = Translation{trans_id, translation};
        let available: Vec<Translation> = row.get(5);
        Passage{pass: torah_portion, translations: TransData{selected, footnote, url, available}} 
    }
  
    fn key_prefix() ->  &'static str {
        "torah_portion"
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
