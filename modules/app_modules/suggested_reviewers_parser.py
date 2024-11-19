from dataclasses import dataclass
import re
from typing import Optional
import unicodedata

# Allow dashes in names like Machuca-Sepulveda.
NAME = r"[\w\-']+"
# Separate with any number of regular ascii whitespace.
SEP = " +"
EMAIL = r"[\w_\-\.]+@[\w_\-\.]+\.[a-zA-Z]+"
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
class Reviewer:
    suggestor: Optional[FullId]
    suggested: FullId


    @staticmethod
    def parse(input: str) -> "Reviewer":
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
        return Reviewer(suggestor, suggested)


    @staticmethod
    def validate(input: str) -> bool:
        try:
            Reviewer.parse(input)
            return True
        except ParseError:
            return False


    @staticmethod
    def error(input: str) -> Optional[str]:
        try:
            Reviewer.parse(input)
            return None
        except ParseError as e:
            return f"{e}"


def strip_accents(s: str):
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


########################################################################################
# Successful parses.

Reviewer.parse("Marc-Olivier Durisson")
Reviewer.parse("Marc-Olivier Durisson suggested: Antonio Patate")
Reviewer.parse("Antonio Patate antonio.patate@usys.ethz.ch")
Reviewer.parse(
    "Marc-Olivier Durisson suggested: " "Antonio Patate antonio.patate@usys.ethz.ch"
)
Reviewer.parse(
    "Marc-Olivier Durisson marc-olivier.durisson@bat.be suggested: Antonio Patate"
)
Reviewer.parse(
    "Marc-Olivier Dùrisson marc-olivier.durisson@bat.be suggested: "
    "Antonio Patate antonio.patate@usys.ethz.ch"
)
Reviewer.parse(
    "toto titi suggested: Jéan-Marc De La Brënche hello-world.Yaguö@test.cefe.cnrs.fr"
)
Reviewer.parse("toto titi suggested: Jéan-Marcy De La Brënche")
Reviewer.parse("Caroline JOYAUX suggested: Pierre-Jean Boubib boubib@mnhn.fr")
Reviewer.parse("thom pci john@doe.com suggested: John Doe john@doe.com")
Reviewer.parse("thom pci suggested: John Doe john@doe.com")
Reviewer.parse("Jéan-Marc De La Brënche hello-world.Yaguö@test.cefe.cnrs.fr")
Reviewer.parse("Jéan-Marc De La Brënche")
Reviewer.parse("toto titi suggested: toto tutu")
Reviewer.parse("toto titi suggested: toto tutu@tef.fr")
Reviewer.parse("AOUE E O'connor tutu@tef.fr")

########################################################################################
# Failed parses.

# Reviewer.parse(" ")  # Not a valid name: ''.
# Reviewer.parse("a+5")  # Not a valid name: 'a+5'.
# Reviewer.parse("A B.. C")  # Not a valid name: 'B.'.
# Reviewer.parse("A B suggested: C D suggested: E F")  # Not a valid name: 'suggested:'.
# Reviewer.parse(
#     "A B. suggested: C D."  # Last name looks like an abbreviated first name: 'B.'.
# )
