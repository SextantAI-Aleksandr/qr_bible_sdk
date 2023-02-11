
use qrcodegen::{QrCode, QrCodeEcc};


const BASE_URL: &'static str = "https://qrbible.app/";


pub trait ToQR {
    fn index(&self) -> &'static str; // give the index or "type" of struct
    fn pk(&self) -> String;
    fn url(&self) -> String {
        // return the URL for this object 
        format!("{}/{}/{}", BASE_URL, self.index(), self.pk())
    }
    fn qr_code(&self) -> QrCode {
        QrCode::encode_text(&self.url(), QrCodeEcc::Medium).unwrap() 
    }
}




// Prints the given QrCode object to the console for development purposes 
// Credit: https://github.com/nayuki/QR-Code-generator/blob/master/rust/examples/qrcodegen-demo.rs 
pub fn print_qr(qr: &QrCode) {
	let border: i32 = 4;
	for y in -border .. qr.size() + border {
		for x in -border .. qr.size() + border {
			let c: char = if qr.get_module(x, y) { '█' } else { ' ' };
			print!("{0}{0}", c);
		}
		println!();
	}
	println!();
}
