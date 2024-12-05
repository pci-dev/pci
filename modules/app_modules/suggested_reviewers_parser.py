from dataclasses import dataclass
import re
from typing import Optional
import unicodedata

# Allow dashes in names like Machuca-Sepulveda.
NAME = r"[\w\-']+"
# Separate with any number of regular ascii whitespace.
SEP = " +"
EMAIL = r"[\w_\-\.+]+@[\w_\-\.]+\.[a-zA-Z]+"
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
            email = m.group(2)
        else:
            name = input
            email = None
        name = FullName.parse(name)
        return FullId(name, email)


@dataclass
class NameParser:
    suggestor: Optional[FullId]
    person: FullId


    @staticmethod
    def parse(input: str) -> "NameParser":
        # Possibly a suggestor is input.
        try:
            suggestor, suggested = re.split(
                f"{SEP}{SUGGESTION_SEP}{SEP}",
                input,
                maxsplit=1,
            )
        except ValueError:
            suggestor = None
            suggested = input
        if suggestor is not None:
            suggestor = FullId.parse(suggestor)
        suggested = FullId.parse(suggested)
        return NameParser(suggestor, suggested)


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


########################################################################################
# Successful parses.

NameParser.parse("Marc-Olivier Durisson")
NameParser.parse("Marc-Olivier Durisson suggested: Antonio Patate")
NameParser.parse("Antonio Patate antonio.patate@usys.ethz.ch")
NameParser.parse(
    "Marc-Olivier Durisson suggested: " "Antonio Patate antonio.patate@usys.ethz.ch"
)
NameParser.parse(
    "Marc-Olivier Durisson marc-olivier.durisson@bat.be suggested: Antonio Patate"
)
NameParser.parse(
    "Marc-Olivier Dùrisson marc-olivier.durisson@bat.be suggested: "
    "Antonio Patate antonio.patate@usys.ethz.ch"
)
NameParser.parse(
    "toto titi suggested: Jéan-Marc De La Brënche hello-world.Yaguö@test.cefe.cnrs.fr"
)
NameParser.parse("toto titi suggested: Jéan-Marcy De La Brënche")
NameParser.parse("Caroline JOYAUX suggested: Pierre-Jean Boubib boubib@mnhn.fr")
NameParser.parse("thom pci john@doe.com suggested: John Doe john@doe.com")
NameParser.parse("thom pci suggested: John Doe john@doe.com")
NameParser.parse("Jéan-Marc De La Brënche hello-world.Yaguö@test.cefe.cnrs.fr")
NameParser.parse("Jéan-Marc De La Brënche")
NameParser.parse("toto titi suggested: toto tutu")
NameParser.parse("toto titi suggested: toto tutu@tef.fr")
NameParser.parse("toto titi suggested:  toto reviewer1pci+fake_810@gmail.com")
NameParser.parse("AOUE E O'connor tutu@tef.fr")

########################################################################################
# Failed parses.

# Reviewer.parse(" ")  # Not a valid name: ''.
# Reviewer.parse("a+5")  # Not a valid name: 'a+5'.
# Reviewer.parse("A B.. C")  # Not a valid name: 'B.'.
# Reviewer.parse("A B suggested: C D suggested: E F")  # Not a valid name: 'suggested:'.
# Reviewer.parse(
#     "A B. suggested: C D."  # Last name looks like an abbreviated first name: 'B.'.
# )
