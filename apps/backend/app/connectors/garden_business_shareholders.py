"""POC fixture: mock coShareholdersDetails payload for GARDEN BUSINESS.

The Bizfile Mock sandbox returns `{"entities": []}` for this UEN's
coShareholdersDetails call, even though it exists in
entityBasicInformation. This fixture lets the onboarding happy path be
demonstrated end-to-end in the POC. Remove or replace once the sandbox
dataset covers this entity, and definitely before this connector is
pointed at anything production-like.
"""

GARDEN_BUSINESS_UEN = "11111999A"
SIM_LIM_UEN = "111111111M"

GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY: dict = {
    "entities": [
        {
            "uen": GARDEN_BUSINESS_UEN,
            "name": "GARDEN BUSINESS",
            "shareholders": {
                "individual": [
                    {
                        "shareholderCategory": "Corporate",
                        "shareholderId": SIM_LIM_UEN,
                        "shareholderName": "SIM LIM PTE. LTD.",
                        "shareAllotted": 5000,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2018-03-10",
                        "status": "Active",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S9988776F",
                        "shareholderName": "LIM CHOON HUAT",
                        "shareAllotted": 3000,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2018-03-10",
                        "status": "Active",
                    },
                ],
                "grouping": [],
            },
        }
    ]
}
