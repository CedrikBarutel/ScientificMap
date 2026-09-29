from __future__ import annotations

from .models import Person, normalize_name, split_list


def _names(values: set[str]) -> set[str]:
    return {normalize_name(value) for value in values}


AC_PROFESSORS = _names({
    "Jiehua Chen",
    "Robert Ganian",
    "Martin Nöllenburg",
    "Günther Raidl",
    "Stefan Szeider",
})
AC_OFFICE = _names({"Doris Brazda"})
AC_SYSTEM = _names({"Johannes Strasser"})
AC_SCIENTIFIC = _names({
    "Maria Bresich",
    "Thomas Depian",
    "Sara Di Bartolomeo",
    "Alexander Firbas",
    "Marlene Gründel",
    "Christian Hatschka",
    "Phuc Hung Hoang",
    "Enrico Iurlano",
    "Liana Khazaliya",
    "Markus Kirchweger",
    "Martin Kronegger",
    "Pablo Manrique Merchan",
    "Antonio Mondejar",
    "Tomáš Peitl",
    "Mathis Rocton",
    "Morteza Saghafian",
    "Manuel Sorge",
    "Laurenz Tomandl",
    "Johannes Varga",
    "Florentina Voboril",
    "Simon Wietheger",
    "Hai Xia",
    "Tianwei Zhang",
})
AC_CURRENT = AC_PROFESSORS | AC_OFFICE | AC_SYSTEM | AC_SCIENTIFIC

AC_SOURCE = "https://www.ac.tuwien.ac.at/people/"
AC_HOME = "https://www.ac.tuwien.ac.at/"
BIOPHYSICS_SOURCE = "https://www.tuwien.at/en/phy/iap/biophysics"
ILSB_SOURCE = "https://www.tuwien.at/mwbw/ilsb/en/team/team-biomechanik/"
UNIVIE_COMP_SOURCE = "https://comp-phys.univie.ac.at/people"
MAX_PERUTZ_SOURCE = "https://www.maxperutzlabs.ac.at/research/research-groups"


def _append_sources(person: Person, *urls: str) -> None:
    person.source_urls = split_list(person.source_urls + [url for url in urls if url])


def _refine_ac(person: Person) -> None:
    key = normalize_name(person.name)
    person.institution = "TU Wien"
    person.university = "TU Wien"
    person.faculty = "Faculty of Informatics"
    person.institute = "Institute of Logic and Computation"
    person.unit = ""
    person.group = "Algorithms and Complexity Group"
    person.department = "Algorithms and Complexity Group"
    person.location = person.location or "Favoritenstraße 9–11, 1040 Wien"
    person.affiliation_status = "current" if key in AC_CURRENT else "alumni"

    if key in AC_PROFESSORS:
        person.role = "Professor"
        if key == normalize_name("Stefan Szeider"):
            person.role = "Professor; Head of Algorithms and Complexity Group"
    elif key in AC_OFFICE:
        person.role = "Office Administration"
    elif key in AC_SYSTEM:
        person.role = "System Administration"
    elif key == normalize_name("Tomáš Peitl"):
        person.role = "University Assistant"
    elif key in AC_SCIENTIFIC and not person.role:
        person.role = "Scientific Staff"
    elif person.affiliation_status == "alumni" and not person.role:
        person.role = "Former group member"

    _append_sources(person, AC_HOME, AC_SOURCE)


def _refine_tu_biophysics(person: Person) -> None:
    key = normalize_name(person.name)
    parts = [part.strip() for part in person.department.split("/") if part.strip()]
    person.institution = "TU Wien"
    person.university = "TU Wien"
    person.faculty = "Faculty of Physics"
    person.institute = "Institute of Applied Physics"
    person.unit = "Biophysics Research Unit"
    person.group = parts[-1] if parts else person.group
    person.location = person.location or "Getreidemarkt 9 / Lehargasse 6, 1060 Wien"
    person.affiliation_status = person.affiliation_status or "current"

    if key == normalize_name("Gerhard Schütz"):
        person.email = person.email or "schuetz@iap.tuwien.ac.at"
    elif key == normalize_name("Mario Brameshuber"):
        person.email = person.email or "brameshuber@iap.tuwien.ac.at"
    elif key in {
        normalize_name("Cédrik Marius André Barutel"),
        normalize_name("Jakob Roland Schindelwig"),
        normalize_name("Arun Ravi"),
    }:
        person.role = "Project Assistant; PhD Student"
        person.profile_url = person.profile_url or "https://www.tuwien.at/en/phy/iap/biophysics/team"

    _append_sources(person, BIOPHYSICS_SOURCE, "https://www.tuwien.at/en/phy/iap/biophysics/team")


def _refine_ilsb(person: Person) -> None:
    person.institution = "TU Wien"
    person.university = "TU Wien"
    person.faculty = "Faculty of Mechanical and Industrial Engineering"
    person.institute = "Institute of Lightweight Design and Structural Biomechanics"
    person.unit = "Biomechanics"
    person.group = "Team Biomechanics"
    person.location = person.location or "Getreidemarkt 9, 1060 Wien"
    person.affiliation_status = "current"
    key = normalize_name(person.name)
    if key == normalize_name("Philipp J. Thurner"):
        person.email = person.email or "pthurner@ilsb.tuwien.ac.at"
        person.role = "Professor of Biomechanics; Head of Institute"
        _append_sources(person, "https://www.tuwien.at/mwbw/ilsb/en/team/team-biomechanik/philipp-j-thurner/")
    elif key == normalize_name("Orestis G. Andriotis"):
        person.role = "Senior Scientist"
        _append_sources(person, "https://www.tuwien.at/mwbw/ilsb/en/team/team-biomechanik/orestis-g-andriotis/")
    _append_sources(person, ILSB_SOURCE)


def _refine_univie_comp(person: Person) -> None:
    key = normalize_name(person.name)
    person.institution = "University of Vienna"
    person.university = "University of Vienna"
    person.faculty = "Faculty of Physics"
    person.institute = ""
    person.unit = "Computational and Soft Matter Physics"
    person.affiliation_status = "current"

    if key == normalize_name("Roberto Cerbino"):
        person.group = "Cerbino Group"
        person.location = "Boltzmanngasse 5, 1090 Wien"
        person.email = person.email or "roberto.cerbino@univie.ac.at"
        person.role = "University Professor; Head of Cerbino Group"
    elif key == normalize_name("Christoph Dellago"):
        person.group = "Dellago Group"
        person.location = "Kolingasse 14–16, 1090 Wien"
        person.email = person.email or "christoph.dellago@univie.ac.at"
        person.role = "University Professor; Group Speaker"
    elif key in {normalize_name("Christos N. Likos"), normalize_name("Christos Likos")}:
        person.group = "Likos Group"
        person.location = "Kolingasse 14–16, 1090 Wien"
        person.email = person.email or "christos.likos@univie.ac.at"
        person.role = "University Professor; Head of Likos Group"
    elif key == normalize_name("Sofia Kantorovich"):
        person.group = "Kantorovich Group"
        person.location = "Kolingasse 14–16, 1090 Wien"
        person.role = "University Professor; Deputy Group Speaker"
    _append_sources(person, UNIVIE_COMP_SOURCE, "https://comp-phys.univie.ac.at/research/")


def _refine_max_perutz(person: Person) -> None:
    key = normalize_name(person.name)
    person.institution = "Max Perutz Labs"
    person.institute = "Max Perutz Labs"
    person.unit = "Structural and Computational Biology"
    person.affiliation_status = "current"

    if key == normalize_name("Jonas Ries"):
        person.university = "University of Vienna"
        person.faculty = ""
        person.group = "Super-resolution microscopy for structural cell biology"
        person.role = "Full Professor; Group Leader"
        person.email = "jonas.ries@maxperutzlabs.ac.at"
        person.location = "Vienna BioCenter, Dr.-Bohr-Gasse 9, 1030 Wien"
        _append_sources(person, "https://www.maxperutzlabs.ac.at/research/research-groups/ries")
    elif key in {normalize_name("Jörg Menche"), normalize_name("Jorg Menche")}:
        person.university = "University of Vienna"
        person.faculty = "Faculty of Mathematics"
        person.group = "Quantitative Modelling of Biological Networks"
        person.role = "Professor; Group Leader"
        person.email = person.email or "joerg.menche@univie.ac.at"
        person.location = "Vienna BioCenter, 1030 Wien"
        _append_sources(person, "https://www.maxperutzlabs.ac.at/research/research-groups/menche")
    elif key == normalize_name("Thomas Juffmann"):
        person.university = "University of Vienna"
        person.faculty = "Faculty of Physics"
        person.group = "Quantum Optics and Microscopy"
        person.role = "Group Leader"
        person.email = person.email or "thomas.juffmann@univie.ac.at"
        person.location = "Vienna BioCenter, Dr.-Bohr-Gasse 9, 1030 Wien"
        _append_sources(person, "https://www.maxperutzlabs.ac.at/research/research-groups/juffmann")
    _append_sources(person, MAX_PERUTZ_SOURCE)


def refine_people_metadata(people: list[Person]) -> list[Person]:
    for person in people:
        department = person.department.lower()
        institution = person.institution.lower()

        if department == "algorithms and complexity group":
            _refine_ac(person)
        elif "institute of applied physics" in department and "biophysics research unit" in department:
            _refine_tu_biophysics(person)
        elif "lightweight design and structural biomechanics" in department:
            _refine_ilsb(person)
        elif institution == "university of vienna" and "computational and soft matter physics" in department:
            _refine_univie_comp(person)
        elif "max perutz labs" in institution:
            _refine_max_perutz(person)
        else:
            person.university = person.university or person.institution
            person.group = person.group or person.department

    return people
