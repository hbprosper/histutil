#!/usr/bin/env python
#-----------------------------------------------------------------------------
# File: Make a simple struct that can be used in a C++ program to create a
#       simple (flat) Root n-tuple given a file containing the list of
#       variables and their types, with the following format:
#       type list-of-variables
#       example:
#
#          float weight
#          float pt, eta, phi
#          int njets
#          vector<float> jet_pt, jet_eta, jet_phi
#
#       Why do this? Because I'm tired of writing the same boilerplate code to
#       write flat ntuples.
#
# Created: 25-Oct-2015 Harrison B. Prosper
# Updated: 07-Oct-2016 HBP - slight generalization (allow setting of default
#                      treename)
#-----------------------------------------------------------------------------
import os, sys
from string import *
from time import ctime
#-----------------------------------------------------------------------------
def nameonly(s):
    import posixpath
    return posixpath.splitext(posixpath.split(s)[1])[0]

LTEMPLATE = '''#include <vector>
#include <string>
#include <map>
#ifdef __CINT__
#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;
#pragma link C++ class std::vector<std::vector<int> >+;
#pragma link C++ class std::vector<std::vector<float> >+;
#pragma link C++ class std::map<std::string, float>+;
#pragma link C++ class std::vector<std::vector<double> >+;
#pragma link C++ class std::map<std::string, double>+;
#pragma link C++ class %(structname)s+;
#endif
'''
HTEMPLATE = '''#ifndef %(structname)s_H
#define %(structname)s_H

// Created: %(date)s by makeTstruct.py v1.0.1

#include <vector>
#include <string>
#include <cassert>
#include "TFile.h"
#include "TTree.h"

struct %(structname)s
{
%(variables)s
  //------------------------------------------------------------------------
  %(structname)s()
    : file(0), tree(0), clearvalue(0)
  {}

  %(structname)s(std::string filename,
  %(tab1)sstd::string treename="%(treename)s",
  %(tab1)sstd::string title="%(treename)s",
  %(tab1)sfloat clearvalue_=0)
    : file(0), tree(0), clearvalue(clearvalue_)
  {
    Open(filename, treename, title, clearvalue);
  }

  void Open(std::string filename,
            std::string treename,
            std::string title,
            float clearvalue_)  
  {
    file = 0;
    tree = 0;
    clearvalue = clearvalue_;
    
    file = new TFile(filename.c_str(), "recreate");
    assert(file);
    assert(file->IsOpen());
    
    file->cd();
    tree = new TTree(treename.c_str(), title.c_str());
    assert(tree);
    
%(branches)s
  }
  ~%(structname)s() { delete file; }

  void Clear()
  {
%(clear)s
  }
  
  void Fill()
  {
    file->cd();
    tree->Fill();
  }
  
  void Close()
  {
    file->cd();
    tree->Write();
  }
  
  TFile* file;
  TTree* tree;
  float clearvalue;
};
#endif
'''
#-----------------------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    argc = len(argv)
    if argc < 1:
        sys.exit('''
    Usage:
       makeTstruct.py variables-file [tree-name=Analysis]
        ''')

    # get name of file containing variables
    varfile = argv[0]
    if not os.path.exists(varfile):
        sys.exit("** can't open file %s" % varfile)

    treename = "Analysis"
    if len(argv) > 1:
        treename = argv[1]
        
    name = nameonly(varfile)
    structname = capitalize(name)
    names = {'structname': structname,
             'date': ctime(),
             'tab1': ' '*len(structname)+' ',
             'treename': treename
             }
        
    # read file containing  variables
    records = filter(lambda x: (x[0] != '#') or (x[0] != "/"),
                     filter(lambda x: x != '',
                     map(strip, open(varfile).readlines())))    
    variables = ''
    branches  = ''
    clear     = ''
    for record in records:
        if record[-1] == ';': record = record[:-1]
        record = replace(record, '> >', '@')
        t  = split(record)
        ftype = replace(t[0], '@', '> >')
        
        vectorType = ftype[0] == 'v'
        if vectorType:
            ftype = replace(ftype, 'vector', 'std::vector')
            
        ft = upper(ftype[0])
        
        # get fields
        t  = joinfields(t[1:], '')
        t  = split(t, ",")
        for field in t:
            variables += '  %s\t%s;\n' % (ftype, field)
            if vectorType:
                branches  += '    tree->Branch("%s", "%s", \t&%s);\n' % \
                (field, ftype, field)
                clear     += '    %s.clear();\n' % field               
            else:
                branches  += '    tree->Branch("%s", &%s, \t"%s/%s");\n' % \
                (field, field, field, ft)
                clear     += '    %s\t= clearvalue;\n' % field               
            print "\t%s\t%s" % (ftype, field)
            
    # write out header
    names['variables'] = variables
    names['branches']  = rstrip(branches)
    names['clear']     = rstrip(clear)
    
    header = "%(structname)s.h" % names
    print "\nwriting %s" % header
    record = HTEMPLATE % names
    open(header, "w").write(record)

    linkdef= "%(structname)s_linkdef.h" % names
    print "\nwriting %s" % linkdef
    record = LTEMPLATE % names
    open(linkdef, "w").write(record)    
# -------------------------------------------------------------------------
try:
    main()
except KeyboardInterrupt:
    print "ciao!"
    
