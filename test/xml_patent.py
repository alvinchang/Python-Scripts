from xml.dom import minidom
from types import *
import datetime, csv, os, re, sqlite3
import copy
##import numpy as np
##import scipy as sp
import unicodedata


#def innerHTML(dom_element):
#    #if blank return nothing as well!
#    if dom_element == '':
#        return ''
#    else:
#        rc = ""
#        for node in dom_element.childNodes:
#            if node.nodeType == node.TEXT_NODE:
#                rc = rc + node.data
#        return rc

class XMLPatent:
    def __init__(self, XMLString, debug=False):
        #XMLString conversion so tags are all lower
        XMLString = re.sub(r"<[/]?[A-Za-z-]+?[ >]", lambda x: x.group().lower(), XMLString)
##        XMLString = re.sub(r"(?<![</A-Za-z-])[/]?[A-Za-z-]+?>", lambda x: "<"+x.group().lower(), XMLString)
        xmldoc = minidom.parseString(XMLString)
        #patent related detail
        #  patent number, kind, date_grant, date_app, country, pat_type
        if debug:
            print "  - country, patent, kind, date_grant"
        self.country, self.patent, self.kind, self.date_grant = self.__tagNme__(xmldoc, ["publication-reference", ["country", "doc-number", "kind", "date"]])
        if debug:
            print "  - pat_type"
        self.pat_type = self.__tagNme__(xmldoc, ["application-reference"], iHTML=False)[0].attributes["appl-type"].value
        if debug:
            print "  - date_app, country_app, patent_app"
        self.date_app, self.country_app, self.patent_app = self.__tagNme__(xmldoc, ["application-reference", ["date", "country", "doc-number"]])
        if debug:
            print "  - code_app"
        self.code_app = self.__tagNme__(xmldoc, ["us-application-series-code"])
        if debug:
            print "  - clm_num"
        self.clm_num = self.__tagNme__(xmldoc, ["number-of-claims"])
        if debug:
            print "  - classes"
        self.classes = [[x[:3].replace(' ',''), x[3:].replace(' ','')] for x in self.__tagNme__(xmldoc, ["classification-national", ["main-classification", "further-classification"]], idx=1, listType=True)]

        if debug:
            print "  - abstract"
        self.abstract = self.__allHTML__(xmldoc, ["abstract", "p"])
        if debug:
            print "  - invention_title"
        self.invention_title = self.__allHTML__(xmldoc, ["invention-title"])

        if debug:
            print "  - asg_list"
        self.asg_list = self.__asg_detail__(self.__tagNme__(xmldoc, ["assignees", "assignee"], iHTML=False))
        if debug:
            print "  - cit_list"
        self.cit_list = self.__cit_detail__(self.__tagNme__(xmldoc, ["references-cited", "citation"], iHTML=False))
        if debug:
            print "  - rel_list"
        self.rel_list = self.__rel_detail__(self.__tagNme__(xmldoc, ["us-related-documents"], iHTML=False))

        if debug:
            print "  - inv_list"
        self.inv_list = self.__tagSplit__(xmldoc, ["parties", "applicant"], [["addressbook", ["last-name", "first-name"]], ["addressbook", "address", ["street", "city", "state", "country", "postcode"]], [["nationality", "residence"], "country"]], blank=True)
        if debug:
            print "  - law_list"
        self.law_list = self.__tagSplit__(xmldoc, ["parties", "agents", "agent"], [["addressbook", ["last-name", "first-name", "country", "orgname"]]], blank=True)

    def __allHTML__(self, xmldoc, tagList):
        for x in self.__tagNme__(xmldoc, tagList, iHTML=False):
            return re.sub(r"<[/]?%s( .*?)?>" % (tagList[-1]), "", x.toxml())
        return ""

    def __innerHTML__(self, dom_element):
        #if blank return nothing as well!
        if dom_element == '':
            return ''
        else:
            rc = ""
            for node in dom_element.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    rc = rc + node.data
            return rc

    def __tagSplit__(self, xmldoc, xmlList, tagList, baseList=[], idx=0, blank=False, iHTML=True, debug=False):
        d_list = []
        for x in self.__tagNme__(xmldoc, tagList=xmlList, iHTML=False):
            record = copy.copy(baseList)
            for y in tagList:
                if debug:
                    print "-------------------"
                    print x.toxml()
                    print y
                record.extend(self.__tagNme__(x, tagList=y, blank=blank, iHTML=iHTML, debug=debug, idx=idx))
            d_list.append(record)
        return d_list

    def __tagNme__(self, xmldoc, tagList, idx=0, listType=False, blank=False, iHTML=True, debug=False):
        xmldoc = [xmldoc]
        for i,x in enumerate(tagList):
            if type(x) is not ListType:
                x = [x]
            xmlnext = []
            for y in x:
                for z in xmldoc:
                    if z != '':
                        if i==0 and idx!=0:
                            if len(z.getElementsByTagName(y))>0:
                                xmlnext.append(z.getElementsByTagName(y)[idx-1])
                            else:
                                xmlnext.append('')
                        else:
                            blFlag = False
                            for za in z.getElementsByTagName(y):
                                blFlag = True
                                xmlnext.append(za)
                            if blFlag==False and blank==True:
                                xmlnext.append('')
                    else:
                        xmlnext.append('')
            xmldoc = xmlnext

        if debug:
            if len(xmldoc)==1 and iHTML:
                print self.__innerHTML__(xmldoc[0])
            elif iHTML:
                print [self.__innerHTML__(x) for x in xmldoc]
            else:
                print xmldoc

        if len(xmldoc)==1 and iHTML:
            if listType:
                return [self.__innerHTML__(xmldoc[0])]
            else:
                return self.__innerHTML__(xmldoc[0])
        elif iHTML:
            return [self.__innerHTML__(x) for x in xmldoc]
        else:
            return xmldoc

    def __asg_detail__(self, xmldoc):
        d_list = []
        for x in xmldoc:
            record = []
            if len(x.getElementsByTagName("first-name"))>0:
                record = [1]
                record.extend(self.__tagNme__(x, [["last-name", "first-name"]]))
            else:
                record = [0]
                record.extend(self.__tagNme__(x, [["orgname", "role"]]))
            record.extend(self.__tagNme__(x, ["addressbook", "address", ["street", "city", "state", "country", "postcode"]], blank=True))
            record.extend(self.__tagNme__(x, [["nationality", "residence"], "country"], blank=True))
            d_list.append(record)
        return d_list

    def __cit_detail__(self, xmldoc):
        d_list = []
        for x in xmldoc:
            #this means patcit is part of the XML
            record = [self.__tagNme__(x, ["category"])]
            if len(x.getElementsByTagName("patcit"))>0:
                record.extend(self.__tagNme__(x, ["patcit", ["country", "doc-number", "date", "kind", "name"]], blank=True))
                record.extend([""])
            elif len(x.getElementsByTagName("othercit"))>0:
                record.extend(["", "", "", "", ""])
                record.extend([self.__allHTML__(x, ["othercit"])])
                #probably should grab date information
            else:
                print x.toxml()
            d_list.append(record)
        return d_list

    def __rel_detail__(self, xmldoc, debug=False):
        d_list = []
        for x in xmldoc:
            for y in ["continuation-in-part", "continuation", "division", "reissue"]:
                if len(x.getElementsByTagName(y))>0:
                    d_list.extend(self.__tagSplit__(x, ["relation", "child-doc"], [[["doc-number", "country", "kind"]]], baseList=[y, -1], blank=True))
                    d_list.extend(self.__tagSplit__(x, ["relation", "parent-doc"], [[["doc-number", "country", "kind", "date", "parent-status"]]], baseList=[y, 1], blank=True, idx=1))
                    d_list.extend(self.__tagSplit__(x, ["relation", "parent-doc", "parent-grant-document"], [[["doc-number", "country", "kind", "date", "parent-status"]]], baseList=[y, 1], blank=True))
                    d_list.extend(self.__tagSplit__(x, ["relation", "parent-doc", "parent-pct-document"],  [[["doc-number", "country", "kind", "date", "parent-status"]]], baseList=[y, 1], blank=True))
            for y in ["related-publication", "us-provisional-application"]:
                if len(x.getElementsByTagName(y))>0:
                    d_list.extend(self.__tagSplit__(x, ["document-id"], [[["doc-number", "country", "kind"]]], baseList=[y, 0], blank=True))
            if debug:
                print "-------------------"
                for x in d_list:
                    print x
        return d_list

    def __repr__(self):
        return \
"""country = %s, patent = %s, pat_type = %s,
date_grant = %s, date_app = %s,
         abstract = %s
  invention_title = %s
len(classes, asg, cit, ret, inv, law) = %s""" % (self.country, self.patent, self.pat_type, self.date_grant, self.date_app,
       self.abstract[:50], self.invention_title[:50],
       str([len(self.classes),  len(self.asg_list), len(self.cit_list),
            len(self.rel_list), len(self.inv_list), len(self.law_list)]))
