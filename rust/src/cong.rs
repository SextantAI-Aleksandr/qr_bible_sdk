use nexum::{postgres as nex_pg};
use visibilis::{postgres as vis_pg};


/// I only anticipate cities being used in the context of finding local congregations
pub struct City {
    pub geo_id: i32,
    pub name: String,
    pub coords: (f64, f64), // lat, long
}

/// An area can be a country of a US State
pub struct Area {
    pub geo_id: i32,
    pub name: String
}


/// An address is simply a street_str plus a city
pub struct Address {
    pub street_str: String, // i.e. 1050 THORNDIKE ST
    pub city: City,
}

/// When someone is searching for a congregation, 
/// They may search by city, US state, or country
pub enum Place {
    Country(Area),
    StateUS(Area),
    City(Area),
}

impl vis_pg::AutoComp<i32> for Place {
    fn query_autocomp() ->  & 'static str {
        "SELECT variant, geo_id, name
        FROM congregation_places_sch
        WHERE ac @@ to_tsquery('simple', $1)
        ORDER BY ct_cong DESC LIMIT 15"
    }
    fn rowfunc_autocomp(row: &nex_pg::Row) -> vis_pg::WhoWhatWhere<i32> {
        let variant: String = row.get(0);
        let pk: i32 = row.get(1);
        let name: String = row.get(2);
        let data_type = match variant.as_ref() {
            "country" => "country",
            "state_us" => "state_us",
            "city" => "city",
            _ => "city", // needed to be exhaustive
        };
        vis_pg::WhoWhatWhere{data_type, pk, name}
    }
}

/// This is a fairly limited view of a congregation (it does not include website, geographic details, EIN etc.)
/// but this is probably still fine for most simple queries
pub struct Congregation {
    pub cong_id: i32,
    pub name: String,
    pub website: Option<String>,
    pub income: Option<u64>,
    pub address: Option<String>,
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
