package shipping

import "fmt"

// FormatPackingSlipAddress renders the destination address printed on our packing slips.
// (Shipping labels themselves come from LabelHub.)
func FormatPackingSlipAddress(a Address) string {
	switch a.Country {
	case "DE":
		return fmt.Sprintf("%s\n%s\n%s %s\nGERMANY", a.Name, a.Street, a.Postcode, a.City)
	case "GB":
		return fmt.Sprintf("%s\n%s\n%s\n%s\nUNITED KINGDOM", a.Name, a.Street, a.City, a.Postcode)
	default:
		return fmt.Sprintf("%s\n%s\n%s %s\n%s", a.Name, a.Street, a.Postcode, a.City, a.Country)
	}
}
