/**
 * Country → phone rules used by the vendor-portal profile-edit dialog.
 *   dial    — international calling prefix (no '+')
 *   digits  — expected number of NATIONAL digits (excl. prefix)
 *   name    — friendly label for the dropdown
 */
export const COUNTRY_PHONE = [
  { code: "KZ", dial: "7",   digits: 10, name: "Kazakhstan" },
  { code: "RU", dial: "7",   digits: 10, name: "Russia" },
  { code: "UZ", dial: "998", digits: 9,  name: "Uzbekistan" },
  { code: "KG", dial: "996", digits: 9,  name: "Kyrgyzstan" },
  { code: "TJ", dial: "992", digits: 9,  name: "Tajikistan" },
  { code: "TM", dial: "993", digits: 8,  name: "Turkmenistan" },
  { code: "AZ", dial: "994", digits: 9,  name: "Azerbaijan" },
  { code: "AM", dial: "374", digits: 8,  name: "Armenia" },
  { code: "GE", dial: "995", digits: 9,  name: "Georgia" },
  { code: "TR", dial: "90",  digits: 10, name: "Turkey" },
  { code: "AE", dial: "971", digits: 9,  name: "United Arab Emirates" },
  { code: "SA", dial: "966", digits: 9,  name: "Saudi Arabia" },
  { code: "QA", dial: "974", digits: 8,  name: "Qatar" },
  { code: "OM", dial: "968", digits: 8,  name: "Oman" },
  { code: "BH", dial: "973", digits: 8,  name: "Bahrain" },
  { code: "KW", dial: "965", digits: 8,  name: "Kuwait" },
  { code: "IN", dial: "91",  digits: 10, name: "India" },
  { code: "PK", dial: "92",  digits: 10, name: "Pakistan" },
  { code: "CN", dial: "86",  digits: 11, name: "China" },
  { code: "KR", dial: "82",  digits: 10, name: "South Korea" },
  { code: "JP", dial: "81",  digits: 10, name: "Japan" },
  { code: "SG", dial: "65",  digits: 8,  name: "Singapore" },
  { code: "GB", dial: "44",  digits: 10, name: "United Kingdom" },
  { code: "DE", dial: "49",  digits: 11, name: "Germany" },
  { code: "FR", dial: "33",  digits: 9,  name: "France" },
  { code: "IT", dial: "39",  digits: 10, name: "Italy" },
  { code: "ES", dial: "34",  digits: 9,  name: "Spain" },
  { code: "US", dial: "1",   digits: 10, name: "United States" },
  { code: "LU", dial: "352", digits: 9,  name: "Luxembourg" },
  { code: "CH", dial: "41",  digits: 9,  name: "Switzerland" },
];

export function phoneSpecFor(code) {
  return COUNTRY_PHONE.find((c) => c.code === code) || COUNTRY_PHONE[0];
}

/**
 * Validate that the typed local digits match the selected country's rule.
 * Returns null on success, or a human-readable error string.
 */
export function validatePhoneForCountry(code, localDigits) {
  const spec = phoneSpecFor(code);
  const digits = String(localDigits || "").replace(/\D/g, "");
  if (!digits) return "Please enter a phone number.";
  if (digits.length !== spec.digits) {
    return `${spec.name} ${spec.digits === 10 ? "mobile" : "phone"} numbers must be exactly ${spec.digits} digits (you entered ${digits.length}).`;
  }
  return null;
}
