import json

from leettools.common.utils.json_utils import ensure_json_item_list


def test_fix_json_list():
    # Example JSON string with an incomplete item
    json_string = """
    {
    "items": [
        {
        "name": "Apheris",
        "description": "Berlin-based startup focused on secure data networks.",
        "industry": "Life Sciences",
        "main_product_or_service": "Secure, collaborative data networks"
        },
        {
        "name": "Jentic",
        "description": "Irish startup focused on building the integration layer for AI.",
        "industry": "Artificial Intelligence",
        "main_product_or_service": "Integration layer for AI"
        },
        {
        "name": "Swave Photonics",
        "details": {
            "founding_year": 2022,
            "hq": "Belgium",
            "notes": "Innovative startup with potential in optics"
        }
        },
        {
        "name": "Incomplete Startup",
        "details": {
            "founding_year": 2022,
            "hq": "Belgium",
            "notes": "Innovative startup with potential in optics"
        },
        "description": "This entry is not complete
    """

    expected_fixed_json = """{
  "items": [
    {
      "name": "Apheris",
      "description": "Berlin-based startup focused on secure data networks.",
      "industry": "Life Sciences",
      "main_product_or_service": "Secure, collaborative data networks"
    },
    {
      "name": "Jentic",
      "description": "Irish startup focused on building the integration layer for AI.",
      "industry": "Artificial Intelligence",
      "main_product_or_service": "Integration layer for AI"
    },
    {
      "name": "Swave Photonics",
      "details": {
        "founding_year": 2022,
        "hq": "Belgium",
        "notes": "Innovative startup with potential in optics"
      }
    }
  ]
}"""

    # Fix the JSON
    fixed_json = ensure_json_item_list(json_string)

    assert fixed_json is not None
    assert fixed_json == expected_fixed_json

    fixed_json = ensure_json_item_list(expected_fixed_json)
    assert fixed_json is not None
    assert fixed_json == expected_fixed_json

    invalid_json_string = """[
    {
        "name": "Apheris",
        "description": "Berlin-based startup focused on secure data networks.",
        "industry": "Life Sciences",
        "main_product_or_service": "Secure, collaborative data networks"
    },
    {
        "name": "Jentic",
        "description": "Irish startup focused on building the integration layer for AI.",
        "industry": "Artificial Intelligence",
        "main_product_or_service": "Integration layer for AI"
    },
    {
        "name": "Swave Photonics",
        "details": {
            "founding_year": 2022,
            "hq": "Belgium",
            "notes": "Innovative startup with potential in optics"
        }
    }
"""
    try:
        ensure_json_item_list(invalid_json_string)
        assert False
    except ValueError as e:
        assert "Invalid JSON string, expected to start with " in str(e)

    invalid_json_string = """{
        "name": "Apheris",
        "description": "Berlin-based startup focused on secure data networks.",
        "industry": "Life Sciences",
        "main_product_or_service": "Secure, collaborative data networks"
    }"""
    try:
        ensure_json_item_list(invalid_json_string)
        assert False
    except ValueError as e:
        assert "Invalid JSON string, expected to start with " in str(e)

    json_string = """
    {"items" : 
    
    [
        {
        "name": "Apheris",
        "description": "Berlin-based startup focused on secure data networks.",
        "industry": "Life Sciences",
        "main_product_or_service": "Secure, collaborative data networks"
        },
    """
    fixed_json = ensure_json_item_list(json_string)
    assert fixed_json is not None

    obj_dict = json.loads(fixed_json)
    assert obj_dict is not None
    assert "items" in obj_dict
    assert len(obj_dict["items"]) == 1
    assert obj_dict["items"][0]["name"] == "Apheris"
    assert (
        obj_dict["items"][0]["description"]
        == "Berlin-based startup focused on secure data networks."
    )
    assert obj_dict["items"][0]["industry"] == "Life Sciences"
