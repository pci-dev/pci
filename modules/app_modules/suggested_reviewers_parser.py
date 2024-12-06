from dataclasses import dataclass
import re
from typing import List, Optional
import unicodedata

# Allow dashes in names like Machuca-Sepulveda.
NAME = r"""[\w\-\-\֊\᠆\‐\‑\‧\⁃\﹣\－\'\"\‘\’\‛\“\”\‟\❛\❜\❝\❞\＂\🙶\🙷\`\‒\–\—\;]+"""
# Separate with any number of regular ascii whitespace.
SEP = " +"
EMAIL = r"(\W+)?[\w_\-\.+]+@[\w_\-\.]+\.[a-zA-Z]+\W?(\W+)?"
SUGGESTION_SEP = "suggested:"


class ParseError(Exception):
    pass


@dataclass
class FullName:

    first: Optional[str]
    last: str


    @staticmethod
    def parse(input: str) -> "FullName":
        # Check every name separately.
        names: list[str] = re.split(SEP, input.strip())
        n = len(names)
        for i, name in enumerate(names):
            # Authorize abbreviated names (ending with '.') unless it's the last one.
            if name.endswith("."):
                if i == n - 1:
                    raise ParseError(
                        "Last name looks like an abbreviated first name: "
                        f"{repr(names[-1])}."
                    )
                else:
                    name = name[:-1]

            name = strip_accents(name)
            if not re.match(NAME + "$", name):
                raise ParseError(f"Not a valid name: {repr(name)}.")
        if not names:
            raise ParseError(f"No names provided: {repr(input)}.")
        first = " ".join(names[:-1]) if len(names) > 1 else None
        last = names[-1]
        return FullName(first, last)


@dataclass
class FullId:
    name: FullName
    email: Optional[str]


    @staticmethod
    def parse(input: str) -> "FullId":
        # Seek optional email at the end.
        if m := re.match(f"^(.*){SEP}({EMAIL})$", input):
            name = m.group(1)
            email = clean_email(str(m.group(2)))
        else:
            name = input
            email = None
        name = FullName.parse(name)
        return FullId(name, email)


@dataclass
class NameParser:
    suggestor: Optional[FullId]
    person: FullId


    def format(self):
        name: List[str] = []
        if self.suggestor:
            if self.suggestor.name.first:
                name.append(self.suggestor.name.first)
            if self.suggestor.name.last:
                name.append(self.suggestor.name.last)
            if self.suggestor.email:
                name.append(self.suggestor.email)
            name.append("suggested:")
        
        if self.person.name.first:
            name.append(self.person.name.first)
        if self.person.name.last:
            name.append(self.person.name.last)
        if self.person.email:
            name.append(self.person.email)
        
        return " ".join(name)


    @staticmethod
    def parse(input: str) -> "NameParser":
        # Possibly a suggestor is input.
        input = input.strip()

        try:
            suggestor, person = re.split(
                f"{SEP}{SUGGESTION_SEP}{SEP}",
                input,
                maxsplit=1,
            )
        except ValueError:
            suggestor = None
            person = input
        if suggestor is not None:
            suggestor = FullId.parse(suggestor)
        person = FullId.parse(person)
        return NameParser(suggestor, person)


    @staticmethod
    def validate(input: str) -> bool:
        try:
            NameParser.parse(input)
            return True
        except ParseError:
            return False


    @staticmethod
    def error(input: str) -> Optional[str]:
        try:
            NameParser.parse(input)
            return None
        except ParseError as e:
            return f"{e}"


def strip_accents(s: str):
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def clean_email(email: str):
    while not email[0].isalnum() or not email[-1].isalnum():
        if not email[0].isalnum():
            email = email[1:]
        if not email[-1].isalnum():
            email = email[:-1]

    return email


########################################################################################
# Successful parses.

# print(NameParser.parse("Marc-Olivier‘ Durisson Niña df    [[(c.m@test.fr]*]  ").format())
# print(NameParser.parse("Marc-Olivier‘ Durisson Niña \"df    (c.m@test.fr )  "))
# print(NameParser.parse("Marc-Olivier Durisson suggested: Antonio Patate"))
# print(NameParser.parse("Antonio Patate antonio.patate@usys.ethz.ch"))
# print(NameParser.parse("Marc-Olivier Durisson suggested: " "Antonio Patate antonio.patate@usys.ethz.ch"))
# print(NameParser.parse("Marc-Olivier Durisson marc-olivier.durisson@bat.be suggested: Antonio Patate"))
# print(NameParser.parse("Marc-Olivier Dùrisson marc-olivier.durisson@bat.be suggested: " "Antonio Patate antonio.patate@usys.ethz.ch"))
# print(NameParser.parse("toto titi suggested: Jéan-Marc De La Brënche hello-world.Yaguö@test.cefe.cnrs.fr"))
# print(NameParser.parse("toto titi suggested: Jéan-Marcy De La Brënche"))
# print(NameParser.parse("Caroline JOYAUX suggested: Pierre-Jean Boubib boubib@mnhn.fr"))
# print(NameParser.parse("thom pci john@doe.com suggested: John Doe john@doe.com"))
# print(NameParser.parse("thom pci suggested: John Doe john@doe.com"))
# print(NameParser.parse("Jéan-Marc De La Brënche hello-world.Yaguö@test.cefe.cnrs.fr"))
# print(NameParser.parse("Jéan-Marc De La Brënche"))
# print(NameParser.parse("toto titi suggested: toto tutu"))
# print(NameParser.parse("toto titi suggested: toto tutu@tef.fr"))
# print(NameParser.parse("toto titi suggested:  toto reviewer1pci+fake_810@gmail.com"))
# print(NameParser.parse("AOUE E O'connor tutu@tef.fr"))

########################################################################################
# Failed parses.

# NameParser.parse(" ")  # Not a valid name: ''.
# NameParser.parse("a+5")  # Not a valid name: 'a+5'.
# NameParser.parse("A B.. C")  # Not a valid name: 'B.'.
# print(NameParser.parse("A B suggested: C D suggested: E F"))  # Not a valid name: 'suggested:'.
# NameParser.parse("A B. suggested: C D.")  # Last name looks like an abbreviated first name: 'B.'.)
