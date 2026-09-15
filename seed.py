"""Load sample members and Atlanta-area garages.

Usage: python seed.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

from app.config import Config
from app.database.store import Database
from app.models import Garage, Policyholder


POLICYHOLDERS = [
    Policyholder(
        id=None,
        name="Maya Chen",
        phone="404-555-0101",
        policy_number="POL-1001",
        policy_doc="roadside-standard",
        status="active",
        listed_drivers="Maya Chen",
        vehicle="2019 Honda Civic",
        address="123 Piedmont Ave NE, Atlanta, GA",
        lat=33.7840,
        lng=-84.3790,
    ),
    Policyholder(
        id=None,
        name="James Okonkwo",
        phone="404-555-0102",
        policy_number="POL-2208",
        policy_doc="roadside-plus",
        status="active",
        listed_drivers="James Okonkwo, Amara Okonkwo",
        vehicle="2021 Ford F-150",
        address="45 Sycamore St, Decatur, GA",
        lat=33.7750,
        lng=-84.2960,
    ),
    Policyholder(
        id=None,
        name="Priya Shah",
        phone="404-555-0103",
        policy_number="POL-1844",
        policy_doc="roadside-standard",
        status="active",
        listed_drivers="Priya Shah",
        vehicle="2020 Toyota Camry",
        address="3500 Peachtree Rd NE, Atlanta, GA",
        lat=33.8480,
        lng=-84.3640,
    ),
    Policyholder(
        id=None,
        name="Derek Walsh",
        phone="404-555-0104",
        policy_number="POL-4410",
        policy_doc="lapsed-notice",
        status="lapsed",
        listed_drivers="Derek Walsh",
        vehicle="2018 Ford Mustang",
        address="800 Moreland Ave SE, Atlanta, GA",
        lat=33.7540,
        lng=-84.3490,
    ),
]

GARAGES = [
    Garage(None, "Midtown Mobile Repair", "980 Peachtree St NE, Atlanta", "404-555-2001", 33.7830, -84.3830, "mobile_repair", "24/7"),
    Garage(None, "Peachtree Towing", "200 14th St NW, Atlanta", "404-555-2002", 33.7750, -84.3900, "tow", "24/7"),
    Garage(None, "Decatur Auto Care", "150 E Ponce de Leon Ave, Decatur", "404-555-2003", 33.7755, -84.2965, "mobile_repair,tow", "6a–10p"),
    Garage(None, "Buckhead Body & Tow", "3340 Peachtree Rd NE, Atlanta", "404-555-2004", 33.8390, -84.3800, "tow,body", "24/7"),
    Garage(None, "East Atlanta Garage", "470 Flat Shoals Ave SE, Atlanta", "404-555-2005", 33.7520, -84.3410, "mobile_repair,tow", "7a–7p"),
    Garage(None, "Airport Towing", "2000 Camp Creek Pkwy, Atlanta", "404-555-2006", 33.6410, -84.4280, "tow", "24/7"),
    Garage(None, "Virginia Highland Service", "1006 N Highland Ave NE, Atlanta", "404-555-2007", 33.7820, -84.3520, "mobile_repair", "7a–8p"),
    Garage(None, "West End Motors", "645 Lee St SW, Atlanta", "404-555-2008", 33.7390, -84.4130, "tow,body", "24/7"),
    Garage(None, "Sandy Springs Assist", "5920 Roswell Rd, Sandy Springs", "404-555-2009", 33.9300, -84.3730, "mobile_repair,tow", "6a–11p"),
    Garage(None, "Downtown Quick Fix", "80 Forsyth St SW, Atlanta", "404-555-2010", 33.7550, -84.3900, "mobile_repair", "24/7"),
    Garage(None, "I-85 North Tow", "Buford Hwy @ Clairmont, Atlanta", "404-555-2011", 33.8600, -84.3070, "tow", "24/7"),
    Garage(None, "Grant Park Garage", "400 Boulevard SE, Atlanta", "404-555-2012", 33.7360, -84.3730, "mobile_repair,tow,body", "7a–9p"),
]


def seed(data_dir: str | Path | None = None, reset: bool = False) -> None:
    path = Path(data_dir or Config.DATA_DIR)
    if reset and path.exists():
        shutil.rmtree(path)

    db = Database(path)
    if db.policyholders.all() and db.garages.all():
        return

    if not db.policyholders.all():
        for person in POLICYHOLDERS:
            db.policyholders.add(person)
    if not db.garages.all():
        for garage in GARAGES:
            db.garages.add(garage)


def main() -> None:
    seed(reset=True)
    print("Seeded Northline Assist sample data:")
    print(f"  policyholders={len(POLICYHOLDERS)}  garages={len(GARAGES)}")
    print("  Maya Chen      POL-1001  Standard  (active)")
    print("  James Okonkwo  POL-2208  Plus      (active)")
    print("  Priya Shah     POL-4412  Standard  (active)")
    print("  Derek Walsh    POL-3300  lapsed")
    print(f"  CSV files in: {Config.DATA_DIR}")


if __name__ == "__main__":
    main()
