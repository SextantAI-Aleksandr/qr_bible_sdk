use std::error::Error;
use std::fmt;  
use serde::{Serialize, Deserialize};
use nexum::{core::GenericError, postgres as nex_pg};
use visibilis::{ui, postgres as vis_pg};


/// There are only a few copora so they can be enumerated
#[derive(Serialize, Debug)]
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
            Corpus::Talmud => (2i16, Translation::English),
            Corpus::Josephus => (-99i16, Translation::English), // trans_id TBD
            Corpus::Enoch => (-99i16, Translation::English), // trans_id TBD
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
#[derive(Serialize, Debug)]
pub enum Translation {
    KingJames,
    Lexham,
    Hebrew,
    English
}
impl Translation {
    pub fn from_name(trans_name: &str) -> Result<Self, CorpusError> {
        match trans_name.to_lowercase().as_ref() {
            "king james" => Ok(Translation::KingJames),
            "lexham" => Ok(Translation::Lexham),
            "hebrew" => Ok(Translation::Hebrew),
            "english" => Ok(Translation::English),
            _ => Err(CorpusError{msg: format!("unable to decipher translation '{}'", trans_name)}),
        }
    }
}

/// A Book (i.e. Genesis, Bava Batra, etc.) has a corpus, a unique book_id, and a name
#[derive(Serialize, Debug)]
pub struct Book {
    corpus: Corpus,
    book_id: i16,
    name: String,
}

/// The Verse struct (separate from the VerseText) struct is intended to send all the information about one verse
/// so it can be read/viewed. This may come up often in the context of searching
#[derive(Serialize, Debug)]
pub struct Verse {
    book: Book,
    translation: Translation,
    chap_no: String,
    verse_no: i16,
    text: String,
    html: String,
}


/// The Chapter struct is intended for sending all the information about a chapter so it can be read
#[derive(Serialize, Debug)]
pub struct Chapter {
    pub verses: Vec<Verse>,
}

/// When typing in an autocomp field for a passage, you probably want to see passages and verses in one context
#[derive(Serialize, Debug)]
pub enum Passage {
    Chapter(Chapter),
    Verse(Verse),
}

impl Chapter {
    /// wrap the verse in a passage
    /// This allows easy return of autocomp searches in passge format
    pub fn to_passage(self) -> Passage {
        Passage::Chapter(self)
    }
}


impl Verse {
    /// wrap the verse in a passage
    /// This allows easy return of autocomp searches in passge format
    pub fn to_passage(self) -> Passage {
        Passage::Verse(self)
    }
}





// this function factors out a common way to get verses from an SQL query
fn verse_from_row(row: &nex_pg::Row) -> Verse {
    let corpus_name: String  = row.get(0);
    let book_name: String = row.get(1);
    let trans_name: String = row.get(2);
    let book_id: i16 = row.get(3);
    let chap_no: String = row.get(4);
    let verse_no: i16 = row.get(5);
    let text: String = row.get(6);
    let html: String = row.get(7);
    let corpus = Corpus::from_name(&corpus_name).unwrap();
    let book = Book{corpus, book_id, name: book_name};
    let translation = Translation::from_name(&trans_name).unwrap();    
    let verse = Verse{book, chap_no, translation, verse_no, text, html};
    verse
}


impl vis_pg::GetByPK for Verse {
    // this query can be used with params &[&book_id, &chapter_no, &verse_no]
    fn query_get_by_pk() -> &'static str {
        "SELECT corpus, book, translation, vt.book_id, vt.chapter_no, vt.verse_no, text, html
        FROM verse_text vt
        INNER JOIN books b ON vt.book_id = b.book_id
        INNER JOIN corpora c ON b.corpus_id = c.corpus_id
        INNER JOIN translations trns ON vt.trans_id = trns.trans_id
        WHERE vt.book_id = $1 AND vt.trans_id = $2 AND vt.chapter_no = $3 AND vt.verse_no = $4 "            
    }
    fn rowfunc_get_by_pk(row: &nex_pg::Row) -> Self {
        verse_from_row(row)
    }
}

/// This gets the default translation for a given book
pub async fn get_default_trans_id(client: &nex_pg::Client, book_id: i16) -> Result<i16, GenericError> {
    let query = "SELECT trans_id
        FROM translations t
        INNER JOIN books b ON t.corpus_id = b.corpus_id
        WHERE b.book_id = $1
        ORDER BY priority ASC LIMIT 1 ";
    let rows = client.query(query, &[&book_id]).await?;
    let row = rows.get(0).ok_or(CorpusError{msg: "could not get a default translation row!".to_string()})?;
    let trans_id: i16 = row.get(0);
    Ok(trans_id)
}

/// This method gets a verse with a given or default translation
pub async fn get_verse_by_pk(client: &nex_pg::Client, book_id: i16, trans_opt: Option<i16>, chap_no: &str, verse_no: i16) -> Result<Verse, GenericError> {
    let trans_id = match trans_opt {
        Some(val) => val,
        None => get_default_trans_id(client, book_id).await?,
    };
    let query = "SELECT corpus, book, translation, vt.book_id, vt.chapter_no, vt.verse_no, text, html
    FROM verse_text vt
    INNER JOIN books b ON vt.book_id = b.book_id
    INNER JOIN corpora c ON b.corpus_id = c.corpus_id
    INNER JOIN translations trns ON vt.trans_id = trns.trans_id
    WHERE vt.book_id = $1 AND vt.trans_id = $2 AND vt.chapter_no = $3 AND vt.verse_no = $4"; 
    let rows = client.query(query, &[&book_id, &trans_id, &chap_no, &verse_no]).await?;
    let row = rows.get(0).ok_or(CorpusError{msg: "could not get a matching verse_text row!".to_string()})?;
    let verse = verse_from_row(row);
    Ok(verse)
}

/// since a chapter is a thin wrapper around a vec of verses
/// implementing vis_pg::GetByPK is a bit trickier
/// it is not implemented, but this function provides similar functionality
pub async fn get_chap_by_pk(client: &nex_pg::Client, book_id: i16, trans_opt: Option<i16>, chap_no: &str) -> Result<Chapter, GenericError> {
    let trans_id = match trans_opt {
        Some(val) => val,
        None => get_default_trans_id(client, book_id).await?,
    };
    let query = "SELECT corpus, book, translation, vt.book_id, vt.chapter_no, vt.verse_no, text, html
    FROM verse_text vt
    INNER JOIN books b ON vt.book_id = b.book_id
    INNER JOIN corpora c ON b.corpus_id = c.corpus_id
    INNER JOIN translations trns ON vt.trans_id = trns.trans_id
    WHERE vt.book_id = $1 AND vt.trans_id = $2 AND vt.chapter_no = $3
    ORDER BY verse_no ASC "; 
    let rows = client.query(query, &[&book_id, &trans_id, &chap_no]).await?;
    let verses = rows.iter().map(|row| verse_from_row(row)).collect::<Vec<Verse>>();
    Ok(Chapter{verses})
}


/// AutoComp is only implemented for Passage,
/// as you probably want one place to type and see both verses and chapters...
impl vis_pg::AutoComp<(i16, String, Option<i16>)> for Passage {
    fn query_autocomp() ->  & 'static str {
        "SELECT source, corpus, book_id, book, chap_no, verse_no, len, name
        FROM passage_autocomp
        WHERE ts @@ to_tsquery('simple', $1)
        ORDER BY len DESC LIMIT 12"
    }
    fn rowfunc_autocomp(row: &nex_pg::Row) -> vis_pg::WhoWhatWhere<(i16, String, Option<i16>)> {
        let source: String = row.get(0);
        let corpus_name: String = row.get(1);
        let book_id: i16 = row.get(2);
        let book_name: String = row.get(3);
        let chap_no: String = row.get(4);
        let verse_no: i32 = row.get(5);
        let verse_no = verse_no as i16; // I think the passage_autocomp somehow makes this i32?
        let name: String = row.get(7);
        match source.as_ref() {
            "Verse" => vis_pg::WhoWhatWhere{ data_type: "verse", name,
                pk: (book_id, chap_no, Some(verse_no)),
            },
            _ => vis_pg::WhoWhatWhere{ data_type: "chapter", name,
                pk: (book_id, chap_no, None),
            }
        }
    }
}

/// FullText is only implemented for verses
impl vis_pg::FullText for Verse {
    fn query_fulltext() -> &'static str {
        "WITH tmp AS (
            SELECT corpus, book, translation, vt.book_id, vt.chapter_no, vt.verse_no, text, html,
                ts_rank_cd(to_tsvector('english', vt.text), to_tsquery($1)) AS score
            FROM verse_text vt
            INNER JOIN books b ON vt.book_id = b.book_id
            INNER JOIN corpora c ON b.corpus_id = c.corpus_id
            INNER JOIN translations trns ON vt.trans_id = trns.trans_id
            WHERE vt.ts @@ to_tsquery('english', $1)
        ) SELECT SELECT corpus, book, translation, book_id, chapter_no, verse_no, text, html
        FROM tmp
        ORDER BY score DESC LIMIT 50"
        
    }
    fn rowfunc_fulltext(row: &nex_pg::Row) -> Self {
        verse_from_row(row)
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
