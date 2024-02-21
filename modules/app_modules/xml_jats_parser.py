
import re
from typing import List, Optional
import xml.etree.ElementTree as ET
import lxml.etree as lxml 

class XMLJATSAuthorElement:
    first_name: Optional[str]
    last_name: Optional[str]
    institution: Optional[str]
    country: Optional[str]
    orcid: Optional[str]
    email: Optional[str]


    def __init__(self, xml_root: ET.Element, contrib_el: ET.Element):
        self.first_name = None
        self.last_name = None
        self.institution = None
        self.country = None
        self.orcid = None
        self.email = None
        
        self._explore_names(contrib_el)
        self._explore_orcid(contrib_el)
        self._explore_email(contrib_el)
        
        if not self.email:
            self._explore_corresp(xml_root, contrib_el)
        self._explore_affiliation(xml_root, contrib_el)
        

    def _explore_names(self, contrib_el: ET.Element):
        first_name = contrib_el.findtext("./name/given-names")
        if first_name:
            self.first_name = first_name.strip()

        last_name = contrib_el.findtext("./name/surname")
        if last_name:
            self.last_name = last_name.strip()

    
    def _explore_orcid(self, contrib_el: ET.Element):
        orcid = contrib_el.findtext("./contrib-id")
        if orcid:
            orcid = orcid.replace("http://orcid.org", "")
            orcid = orcid.strip().strip('/').strip()
            self.orcid = orcid


    def _explore_email(self, contrib_el: ET.Element):
        email = contrib_el.findtext("./email")
        if email:
            self.email = email.strip()            


    def _explore_corresp(self, xml_root: ET.Element, contrib_el: ET.Element):
        corresp_ref = contrib_el.find("./xref[@ref-type='corresp']")
        if corresp_ref == None:
            return
        
        corresp_id = corresp_ref.attrib['rid']
        if not corresp_id:
            return
        
        corresp  =xml_root.find(f"./front/article-meta/author-notes/corresp[@id='{corresp_id}']")
        if corresp == None:
            return
        
        email = corresp.findtext("./email")
        if email:
            self.email = email.strip()


    def _explore_affiliation(self, xml_root: ET.Element, contrib_el: ET.Element):
        affilitation_ref = contrib_el.find("./xref[@ref-type='aff']")
        if affilitation_ref == None:
            return
        
        affiliation_id = affilitation_ref.attrib['rid']
        if not affiliation_id:
            return
        
        affiliation = xml_root.find(f"./front/article-meta/contrib-group/aff[@id='{affiliation_id}']")
        if affiliation == None:
            affiliation = xml_root.find(f"./front/article-meta/aff[@id='{affiliation_id}']")
        if affiliation == None:
            return
        
        institution = affiliation.find("./institution")
        if institution != None:
            if institution.text:
                self.institution = institution.text.strip().strip(',').strip()
            if institution.tail:
                if self.institution and not self.institution.endswith(' ') and not institution.tail.startswith((' ', ',', '.')):
                    self.institution += ' '
                tail = institution.tail.strip().strip(',').strip()
                if tail:
                    if not self.institution:
                        self.institution = tail 
                    else:
                        self.institution += tail
            if self.institution:
                self.institution = self.institution.replace("\n", "")
                self.institution = re.sub(r'\s{2,}', ' ', self.institution)
                self.institution = self.institution.strip()
        
        country = affiliation.findtext("./country")
        if country:
            self.country = country.strip()
                    

class XMLJATSArticleElement:
    title: Optional[str]
    authors: List[XMLJATSAuthorElement]
    abstract: Optional[str]
    doi: Optional[str]

    def __init__(self, xml_root: ET.Element):
        self.title = None
        self.authors = []
        self.abstract = None
        self.doi = None

        doi = xml_root.findtext("./front/article-meta/article-id[@pub-id-type='doi']")
        if doi:
            self.doi = f"https://doi.org/{doi.strip()}"

        title = xml_root.findtext("./front/article-meta/title-group/article-title")
        if title:
            self.title = title.strip()

        abstract = xml_root.findtext("./front/article-meta/abstract/p")
        if abstract:
            self.abstract = abstract.strip()

        self.authors = []
        authors = xml_root.findall("./front/article-meta/contrib-group/contrib")
        for author in authors:
            self.authors.append(XMLJATSAuthorElement(xml_root, author))


class XMLJATSParser:

    article: XMLJATSArticleElement

    def __init__(self, filepath: str):
        xml_tree = ET.parse(filepath, lxml.XMLParser(recover=True))
        xml_root = xml_tree.getroot()

        self.article = XMLJATSArticleElement(xml_root)

