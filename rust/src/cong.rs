use nexum::{postgres as nex_pg};
use visibilis::{postgres as vis_pg};
use magellan::{places::{City, Address}, parse::Place};


/// This struct represents a church, synagogue, etc. 
pub struct Congregation {
    pub cong_id: i32,
    pub name: String,
    pub website: Option<String>,
    pub income: Option<u64>,
    pub address: Option<Address>
}


impl vis_pg::AutoComp<i32> for Congregation {
    fn query_autocomp() ->  & 'static str {
        "SELECT cs.cong_id, cs.name, cs.street_str, cs.city
        FROM congregation_search cs
        WHERE ts @@ to_tsquery('simple', $1)
        LIMIT 15"
    }
    fn rowfunc_autocomp(row: &nex_pg::Row) -> vis_pg::WhoWhatWhere<i32> {
        let pk: i32 = row.get(0);
        let mut name: String = row.get(1);
        let street_str: Option<String> = row.get(2);
        let city_str: Option<String> = row.get(3);
        match (street_str, city_str) {
           (Some(street), Some(city)) => {
                name = format!("{} {}, {}", name, street, city);
           },
           _ => ()
        }
        vis_pg::WhoWhatWhere{data_type: "congregation", pk, name}
    }
}
