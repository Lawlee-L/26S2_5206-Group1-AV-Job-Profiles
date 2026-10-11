import unittest

from database.importer.location_parser import ParsedLocation, parse_location


class LocationParserTests(unittest.TestCase):

    def test_none_and_empty_location_return_null_fields(self):
        self.assertEqual(parse_location(None), ParsedLocation())
        self.assertEqual(parse_location(""), ParsedLocation())
        self.assertEqual(parse_location("   "), ParsedLocation())

    def test_explicit_country_location(self):
        self.assertEqual(
            parse_location("Stuttgart, BW, Germany"),
            ParsedLocation(
                city="Stuttgart",
                state_region="BW",
                country_code="DE",
            ),
        )

    def test_us_state_code_implies_country(self):
        self.assertEqual(
            parse_location("Foster City, CA"),
            ParsedLocation(
                city="Foster City",
                state_region="CA",
                country_code="US",
            ),
        )

    def test_canadian_province_code_implies_country(self):
        self.assertEqual(
            parse_location("Toronto, ON"),
            ParsedLocation(
                city="Toronto",
                state_region="ON",
                country_code="CA",
            ),
        )

    def test_reliable_city_mapping_can_infer_country(self):
        self.assertEqual(
            parse_location("Tokyo"),
            ParsedLocation(
                city="Tokyo",
                country_code="JP",
            ),
        )


if __name__ == "__main__":
    unittest.main()


class LocationParserEdgeCaseTests(unittest.TestCase):

    def test_work_mode_suffix_is_removed(self):
        self.assertEqual(
            parse_location("Ann Arbor, MI - Hybrid"),
            ParsedLocation(
                city="Ann Arbor",
                state_region="MI",
                country_code="US",
                remote_type="hybrid",
            ),
        )

    def test_country_first_chinese_location(self):
        self.assertEqual(
            parse_location("China, Guangdong, Guangzhou City, Haizhu District"),
            ParsedLocation(
                city="Guangzhou City",
                state_region="Guangdong",
                country_code="CN",
            ),
        )

    def test_city_with_explicit_country(self):
        self.assertEqual(
            parse_location("Pangyo (Software Dream Center), South Korea"),
            ParsedLocation(
                city="Pangyo (Software Dream Center)",
                country_code="KR",
            ),
        )

    def test_multiple_us_locations_keep_only_country(self):
        self.assertEqual(
            parse_location("Pittsburgh, PA, Palo Alto, CA, Detroit, MI"),
            ParsedLocation(country_code="US"),
        )

    def test_multiple_chinese_cities_keep_only_country(self):
        self.assertEqual(
            parse_location("Beijing, Nanjing, Shanghai"),
            ParsedLocation(country_code="CN"),
        )

    def test_multiple_countries_are_ambiguous(self):
        self.assertEqual(
            parse_location(
                "San Jose, California, US | Barcelona, Catalonia, Spain | "
                "Singapore | Dubai, UAE"
            ),
            ParsedLocation(),
        )

    def test_long_non_location_text_is_not_guessed(self):
        self.assertEqual(
            parse_location(
                "(Immediately after hiring)\n"
                "Location designated by the company\n"
                "(Potential Changes)\n"
                "Any location designated by the company"
            ),
            ParsedLocation(),
        )


class LocationParserWorkModeTests(unittest.TestCase):

    def test_hybrid_is_preserved(self):
        result = parse_location("Ann Arbor, MI - Hybrid")
        self.assertEqual(result.remote_type, "hybrid")

    def test_remote_is_preserved(self):
        result = parse_location("USA - Remote")
        self.assertEqual(result.remote_type, "remote")

    def test_fully_remote_is_normalised_to_remote(self):
        result = parse_location(
            "Austin, Texas, United States of America (Fully remote)"
        )
        self.assertEqual(result.remote_type, "remote")

    def test_onsite_is_preserved(self):
        result = parse_location("Arlington, TX - Onsite")
        self.assertEqual(result.remote_type, "onsite")

    def test_location_without_work_mode_has_null_remote_type(self):
        result = parse_location("Stuttgart, BW, Germany")
        self.assertIsNone(result.remote_type)


class LocationParserFullStateNameTests(unittest.TestCase):

    def test_us_full_state_name_implies_country(self):
        result = parse_location("Austin, Texas")
        self.assertEqual(
            result,
            ParsedLocation(
                city="Austin",
                state_region="TX",
                country_code="US",
            ),
        )

    def test_california_full_name_implies_country(self):
        result = parse_location("San Luis Obispo, California")
        self.assertEqual(
            result,
            ParsedLocation(
                city="San Luis Obispo",
                state_region="CA",
                country_code="US",
            ),
        )

    def test_north_carolina_full_name_implies_country(self):
        result = parse_location("Winston-Salem, North Carolina")
        self.assertEqual(
            result,
            ParsedLocation(
                city="Winston-Salem",
                state_region="NC",
                country_code="US",
            ),
        )

    def test_full_state_name_with_remote_mode(self):
        result = parse_location(
            "Austin, Texas, United States of America (Fully remote)"
        )
        self.assertEqual(result.city, "Austin")
        self.assertEqual(result.state_region, "TX")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")


class LocationParserAnnotationTests(unittest.TestCase):

    def test_hq_annotation_does_not_block_location_parsing(self):
        result = parse_location("Mountain View, California (HQ)")
        self.assertEqual(
            result,
            ParsedLocation(
                city="Mountain View",
                state_region="CA",
                country_code="US",
            ),
        )


class LocationParserCountryOnlyTests(unittest.TestCase):

    def test_country_only_location(self):
        result = parse_location("Germany")
        self.assertEqual(
            result,
            ParsedLocation(country_code="DE"),
        )

    def test_country_only_japan(self):
        result = parse_location("Japan")
        self.assertEqual(
            result,
            ParsedLocation(country_code="JP"),
        )

    def test_country_only_with_remote_mode(self):
        result = parse_location("USA - Remote")
        self.assertEqual(
            result,
            ParsedLocation(
                country_code="US",
                remote_type="remote",
            ),
        )


class LocationParserMultipleLocationTests(unittest.TestCase):

    def test_semicolon_locations_same_country_keep_country(self):
        result = parse_location(
            "China, Shanghai, Xuhui District; "
            "China, Guangdong, Shenzhen, Futian District"
        )
        self.assertEqual(
            result,
            ParsedLocation(country_code="CN"),
        )

    def test_semicolon_locations_different_countries_are_ambiguous(self):
        result = parse_location(
            "Austin, TX, USA; Stockholm, Sweden"
        )
        self.assertEqual(
            result,
            ParsedLocation(),
        )


class LocationParserJapanTests(unittest.TestCase):

    def test_tokyo_prefecture_implies_japan(self):
        result = parse_location("Chuo-ku, Tokyo")
        self.assertEqual(
            result,
            ParsedLocation(
                city="Chuo-ku",
                state_region="Tokyo",
                country_code="JP",
            ),
        )

    def test_japanese_prefecture_implies_japan(self):
        result = parse_location("Susono, Shizuoka")
        self.assertEqual(
            result,
            ParsedLocation(
                city="Susono",
                state_region="Shizuoka",
                country_code="JP",
            ),
        )

    def test_prefecture_suffix_is_normalised(self):
        result = parse_location("Susono City, Shizuoka Prefecture")
        self.assertEqual(
            result,
            ParsedLocation(
                city="Susono City",
                state_region="Shizuoka",
                country_code="JP",
            ),
        )


class LocationParserCityOnlyTests(unittest.TestCase):

    def test_ann_arbor_city_only(self):
        self.assertEqual(
            parse_location("Ann Arbor").country_code,
            "US",
        )

    def test_stuttgart_city_only(self):
        self.assertEqual(
            parse_location("Stuttgart").country_code,
            "DE",
        )

    def test_seoul_city_only(self):
        self.assertEqual(
            parse_location("Seoul").country_code,
            "KR",
        )

    def test_stockholm_city_only(self):
        self.assertEqual(
            parse_location("Stockholm").country_code,
            "SE",
        )

    def test_tel_aviv_city_only(self):
        self.assertEqual(
            parse_location("Tel Aviv").country_code,
            "IL",
        )

    def test_shenzhen_city_only(self):
        self.assertEqual(
            parse_location("Shenzhen").country_code,
            "CN",
        )

    def test_ambiguous_vancouver_remains_unresolved(self):
        self.assertIsNone(
            parse_location("Vancouver").country_code
        )

    def test_remote_only_remains_without_country(self):
        result = parse_location("Remote")
        self.assertIsNone(result.country_code)
        self.assertEqual(result.remote_type, "remote")


class LocationParserRemoteCountryTests(unittest.TestCase):

    def test_remote_us(self):
        result = parse_location("Remote US")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_remote_us_with_periods(self):
        result = parse_location("Remote U.S.")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_remote_dash_us(self):
        result = parse_location("Remote - US")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_remote_germany(self):
        result = parse_location("Remote - Germany")
        self.assertEqual(result.country_code, "DE")
        self.assertEqual(result.remote_type, "remote")

    def test_remote_without_country_stays_unresolved(self):
        result = parse_location("Remote")
        self.assertIsNone(result.country_code)
        self.assertEqual(result.remote_type, "remote")


class LocationParserJoinedCitiesTests(unittest.TestCase):

    def test_and_joined_cities_same_country_keep_country(self):
        result = parse_location("Beijing and Nanjing")
        self.assertEqual(
            result,
            ParsedLocation(country_code="CN"),
        )

    def test_and_joined_locations_different_countries_are_ambiguous(self):
        result = parse_location("London and Sunnyvale")
        self.assertEqual(
            result,
            ParsedLocation(),
        )


class LocationParserAdditionalCountryTests(unittest.TestCase):

    def test_gothenburg_sweden(self):
        result = parse_location("Gothenburg, Sweden")
        self.assertEqual(result.city, "Gothenburg")
        self.assertEqual(result.country_code, "SE")

    def test_warsaw_poland(self):
        result = parse_location("Warsaw, Poland")
        self.assertEqual(result.city, "Warsaw")
        self.assertEqual(result.country_code, "PL")

    def test_multiple_swedish_locations_keep_country_only(self):
        result = parse_location(
            "Stockholm, Sweden; Gothenburg, Sweden"
        )
        self.assertIsNone(result.city)
        self.assertEqual(result.country_code, "SE")


class LocationParserAdditionalUSPatternsTests(unittest.TestCase):

    def test_washington_dc(self):
        result = parse_location("Washington, D.C.")
        self.assertEqual(result.country_code, "US")

    def test_san_francisco_bay_area(self):
        result = parse_location("San Francisco Bay Area")
        self.assertEqual(result.country_code, "US")

    def test_state_with_city_detail(self):
        result = parse_location("California - LA")
        self.assertEqual(result.country_code, "US")

    def test_state_with_site_detail(self):
        result = parse_location("Texas - Depot 2")
        self.assertEqual(result.country_code, "US")

    def test_state_only(self):
        result = parse_location("Arizona")
        self.assertEqual(result.country_code, "US")

    def test_us_location_with_remote_country(self):
        result = parse_location("Ann Arbor, MI, Remote - US")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_us_location_or_remote(self):
        result = parse_location("Pittsburgh, PA or Remote")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_multiple_us_locations(self):
        result = parse_location("Kermit, TX or Odessa, TX")
        self.assertEqual(result.country_code, "US")

    def test_multiple_us_locations_with_remote(self):
        result = parse_location(
            "Pittsburgh, PA, Palo Alto, CA, Detroit, MI, Remote"
        )
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_remote_and_multiple_us_locations(self):
        result = parse_location(
            "Remote, U.S, Ann Arbor, MI, Fort Worth, TX, Blacksburg, VA"
        )
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")


class LocationParserAdditionalChinaPatternsTests(unittest.TestCase):

    def test_shanghai_district(self):
        result = parse_location("Shanghai - Pudong New Area")
        self.assertEqual(result.country_code, "CN")

    def test_shanghai_and_suzhou(self):
        result = parse_location("Shanghai and Suzhou")
        self.assertEqual(result.country_code, "CN")

    def test_nanjing_city_and_shenzhen_city(self):
        result = parse_location("Nanjing City, Shenzhen City")
        self.assertEqual(result.country_code, "CN")

    def test_chengdu_and_xian(self):
        result = parse_location("Chengdu and Xi'an")
        self.assertEqual(result.country_code, "CN")

    def test_multiple_chinese_cities(self):
        result = parse_location(
            "Beijing, Hangzhou, Nanjing, Shanghai, Shenzhen"
        )
        self.assertEqual(result.country_code, "CN")

    def test_chinese_city_suffix(self):
        result = parse_location("Nanjing City")
        self.assertEqual(result.country_code, "CN")

    def test_chinese_city_with_district(self):
        result = parse_location("Hangzhou City - Binjiang District")
        self.assertEqual(result.country_code, "CN")


class LocationParserLongJapaneseDescriptionTests(unittest.TestCase):

    def test_long_tokyo_assignment_description(self):
        value = """(Immediately after hiring / Initial Assignment)
Jacom Building, 1-12-10 Kita-Shinagawa, Shinagawa-ku, Tokyo; Izumi Kitashinagawa Building, 1-19-4 Kita-Shinagawa, Shinagawa-ku, Tokyo; and workers' homes

(Potential Changes)
Any location designated by the company (including remote work locations)"""

        result = parse_location(value)

        self.assertEqual(result.country_code, "JP")
        self.assertIsNone(result.remote_type)


class LocationParserAdditionalExplicitCountryTests(unittest.TestCase):

    def test_budapest_hungary(self):
        result = parse_location("Budapest, Hungary")
        self.assertEqual(result.country_code, "HU")

    def test_ho_chi_minh_vietnam(self):
        result = parse_location("Ho Chi Minh, Vietnam")
        self.assertEqual(result.country_code, "VN")

    def test_mexico_city_mexico(self):
        result = parse_location("Mexico City, Mexico")
        self.assertEqual(result.country_code, "MX")

    def test_banbury_uk(self):
        result = parse_location("Banbury, UK")
        self.assertEqual(result.country_code, "GB")

    def test_austria_country_only(self):
        result = parse_location("Austria")
        self.assertEqual(result.country_code, "AT")

    def test_one_north_singapore(self):
        result = parse_location("One-north")
        self.assertEqual(result.country_code, "SG")

    def test_bangsar_south_kuala_lumpur(self):
        result = parse_location("Bangsar South, Kuala Lumpur")
        self.assertEqual(result.country_code, "MY")


class LocationParserFinalExplicitPatternsTests(unittest.TestCase):

    def test_california_remote(self):
        result = parse_location("California Remote")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_ajax_ontario(self):
        result = parse_location("Ajax, Ontario")
        self.assertEqual(result.country_code, "CA")

    def test_remote_us_parentheses(self):
        result = parse_location("Remote (US)")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_remote_united_states_parentheses(self):
        result = parse_location("Remote (United States)")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_fort_worth_texas_remote_us(self):
        result = parse_location("Fort Worth, Texas, Remote - US")
        self.assertEqual(result.country_code, "US")
        self.assertEqual(result.remote_type, "remote")

    def test_oklahoma_city(self):
        result = parse_location("Oklahoma City")
        self.assertEqual(result.country_code, "US")

    def test_australia_remote(self):
        result = parse_location("Australia Remote")
        self.assertEqual(result.country_code, "AU")
        self.assertEqual(result.remote_type, "remote")

    def test_nashik_india(self):
        result = parse_location("Nashik, Maharashtra, India")
        self.assertEqual(result.country_code, "IN")

    def test_sao_paulo_brazil(self):
        result = parse_location("São Paulo, Brazil")
        self.assertEqual(result.country_code, "BR")

    def test_multiple_netherlands_locations(self):
        result = parse_location(
            "Netherlands; Amsterdam, Netherlands; Rotterdam, Netherlands; "
            "Utrecht, Netherlands; Hague, Netherlands"
        )
        self.assertEqual(result.country_code, "NL")
