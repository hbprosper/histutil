#!/usr/bin/env python
#------------------------------------------------------------------
# File: writeTMVA.py
# Description: create a more convenient packaging of TMVA MLP/BDTs
#              results.
# Created: 02-Feb-2017 HBP
# Updated: 10-Apr-2017 HBP add ranking
#          12-Apr-2017 HBP improve tree-printing
#------------------------------------------------------------------
import os, sys, re
from string import find, replace
from time import ctime
from ROOT import *
#------------------------------------------------------------------
def nameonly(s):
    import posixpath
    return posixpath.splitext(posixpath.split(s)[1])[0]

getinputvars = re.compile('(?<=const char\* inputVars\[\] = ).*')
getvars      = re.compile('(?<= ").*?(?=",)|(?<= ").*?(?=" )')
getclass     = re.compile('(?<=class )Read.*(?= : public)')
geticlass    = re.compile('class IClassifierReader')
getinclude   = re.compile('#include [<]iostream[>]')
getvirtual   = re.compile('virtual .BDTNode\(\);')
getMvaValueDec     = re.compile('double GetMvaValue[(].*inputValues')
getMvaValue__Dec   = re.compile('double GetMvaValue__[(].*inputValues')
getMvaValueImp     = re.compile('::GetMvaValue[(].*inputValues')
getMvaValue__Imp   = re.compile('::GetMvaValue__[(].*inputValues')
getMvaValueCall = re.compile('retval = GetMvaValue__.*')
getPreamble  = re.compile('::GetMvaValue__.*[^+]+', re.M)
getPublic    = re.compile('class .*public IClassifierReader.*[^:]+:', re.M)
getInputVars = re.compile('const char. inputVars.*[^}]+\}\;', re.M)
#------------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    argc = len(argv)
    if argc < 1:
        sys.exit('''
    Usage:
        ./writeTMVA.py C-filename [output-C++-filename]

    Example:

        ./writeTMVA.py weights/HATS_MLP.class.C  melaMLP
        ''')

    filename = argv[0]
    if argc > 1:
        outfilename = '%s.cc' % nameonly(argv[1])
    else:
        outfilename = '%s.cc' % nameonly(nameonly(filename))
    
    funcname = nameonly(outfilename)
    
    # read code
    code = open(filename).read()

    # get names of input variables
    inputvars = getvars.findall(getinputvars.findall(code)[0])

    # get name of MLP/BDT class
    classname = getclass.findall(code)[0]
    isBDT = find(classname, 'BDT') > -1

    if isBDT:
        x    = getMvaValueDec.findall(code)[0]
        xnew = '%s, int ntrees=0' % x
        code = replace(code, x, xnew)

        x    = getMvaValue__Dec.findall(code)[0]
        xnew = '%s, int ntrees=0' % x
        code = replace(code, x, xnew)

        x    = getMvaValueImp.findall(code)[0]
        xnew = '%s, int ntrees' % x
        code = replace(code, x, xnew)

        x    = getMvaValue__Imp.findall(code)[0]
        xnew = '%s, int ntrees' % x
        code = replace(code, x, xnew)

        x    = getPreamble.findall(code)[0]
        xnew = replace(x, 'fForest.size()', '(size_t)ntrees')
        rec = 'int nsize = (int)fForest.size();\n'\
          '   ntrees = ntrees < 1 ? nsize : ntrees;\n'\
          '   ntrees = ntrees > nsize ? nsize : ntrees;\n'\
          '   for'
        xnew = replace(xnew, 'for', rec)
        code = replace(code, x, xnew)

        x    = getPublic.findall(code)[0]
        xnew = '%s\n'\
          '  size_t size() { return fForest.size(); }\n\n'\
          '  double weight(int itree) { return fBoostWeights[itree]; }\n\n'\
          '  double summedWeights()\n'\
          '  {\n'\
          '    double norm = 0;\n'\
          '    for (size_t itree=0; itree<fForest.size(); itree++)\n'\
          '       norm += fBoostWeights[itree];\n'\
          '    return norm;\n'\
          '  }\n\n' % x
        xnew += \
          '  std::vector<std::string> varnames;\n'\
          '  std::vector<std::string> variables() { return varnames; }\n'

        xnew += '''
  std::vector<std::pair<double, std::string> > ranking(int ntrees=-1)
  {
    size_t maxtrees = ntrees > 0 ? (size_t)ntrees : fForest.size();
    maxtrees = maxtrees > fForest.size() ? fForest.size() : maxtrees;

    std::map<std::string, double> countmap;
    for(size_t c=0; c < varnames.size(); c++) countmap[varnames[c]] = 0;

    for(int itree=0; itree < maxtrees; itree++) __rank(itree, countmap);

    std::vector<std::pair<double, std::string> > countname(varnames.size());
    double total = 0;
    for(size_t c=0; c < varnames.size(); c++)
      {
	countname[c].first  = countmap[varnames[c]];
	countname[c].second = varnames[c];
	total += countname[c].first;
      }
    std::sort(countname.begin(), countname.end());
    std::reverse(countname.begin(), countname.end());
    
    for(size_t c=0; c < countname.size(); c++) countname[c].first /= total;
    return countname;
  }
  
  void __rank(int itree,
	      std::map<std::string, double>& countmap,
	      int depth=0,
	      int which=0,
	      BDTNode* node=0)
  {
    if ( which == 0 )
      node = fForest[itree];
    
    if ( node == 0 ) return;
    if ( node->GetSelector() < 0 ) return;

    std::string name = varnames[node->GetSelector()];
    countmap[name] += 1.0;

    depth++;
    __rank(itree, countmap, depth, -1, node->GetLeft());
    __rank(itree, countmap, depth,  1, node->GetRight());
  }

  void printTree(int itree, 
		 int depth=0, int which=0, BDTNode* node=0)
  {
    printTree(itree, std::cout);
  }
  
  void printTree(int itree, std::ostream& os, 
		 int depth=0, int which=0, BDTNode* node=0)
  {
    char record[80];
    if ( which == 0 )
      {
        node = fForest[itree];
        sprintf(record, "tree number: %d\tweight: %10.3e", 
                itree, fBoostWeights[itree]);
        os << record << std::endl;
      }
    if ( depth > 100 ) return;
    if ( node == 0 ) return;

    int selector = node->GetSelector();
    std::string name("LEAF ");
    if ( selector > -1 )
      name = varnames[node->GetSelector()];
    double value = node->GetCutValue();

    std::string nodedir("");
    if      ( which == 0 )
      nodedir = "root ";
    else if ( which <  0 ) 
      nodedir = "left ";
    else
      nodedir = "right";

    std::string nodetype("");
    if ( node->GetNodeType() < 0 )
      {
	nodetype = "B";
	value = node->GetPurity();
      }
    else if ( node->GetNodeType() > 0 )
      {
	nodetype = "S";
	value = node->GetPurity();
      }
      
    std::string depthstr("  ");
    for(int c=0; c < depth; c++) depthstr += "   ";
    sprintf(record, "%s %10s %10s\t%10.3f %s", depthstr.c_str(),
	    nodedir.c_str(), name.c_str(), value, nodetype.c_str());
    os << record << std::endl;

    depth += 1;
    printTree(itree, os, depth, -1, node->GetLeft());
    printTree(itree, os, depth,  1, node->GetRight());    
  }
  '''
        code = replace(code, x, xnew)
        
        records = getMvaValueCall.findall(code)
        for x in records:
            xnew = '%s, ntrees );' % x[:-3]
            code = getMvaValueCall.sub(xnew, code)

        ntrees0 = ', int ntrees=0'
        ntrees  = ', ntrees'            
    else:
        x    = getPublic.findall(code)[0]
        xnew = '%s\n' \
          '  std::vector<std::string> varnames;\n'\
          '  std::vector<std::string> variables() { return varnames; }\n' % x
          
        code = replace(code, x, xnew)

        ntrees0 = ''
        ntrees  = ''

    # enclose code in an namespace so that class is visible
    # only within the scope of this compilation unit
    code = getinclude.sub('#include <iostream>\n'\
                          '#include <map>\n'\
                          '#include <algorithm>\n\n'\
                          'namespace __%s {' % funcname, code)
                          
    code = getvirtual.sub('virtual ~BDTNode();\n\n'\
                          '  double GetCutValue() const '\
                              '{ return fCutValue; }\n'\
                          '  int    GetSelector() const '\
                              '{ return fSelector; }\n',
                              code)

    recs = getInputVars.findall(code)
    if len(recs) == 0:
        sys.exit('** problem modifying code')
    x = recs[0]
    xnew  = '%s\n' % x
    nvars = len(inputvars)
    xnew += '''
      varnames.clear();
      varnames.resize(%d);
      std::copy(inputVars, inputVars+%d, varnames.begin());
    ''' % (nvars, nvars)
    code = getInputVars.sub(xnew, code)

    # --------------------------------------------------------------------------
    # write C++ function
    # --------------------------------------------------------------------------
    HTAB  = 11*' '
    TAB   = 20*' '
    VTAB  = 23*' '
    ivars = ''
    iargs = ''
    hargs = ''
    tab   = ''
    htab  = ''
    ptab  = '  '
    vtab  = ''
    inpvars = ''
    for ii, v in enumerate(inputvars):
        ivars += '%s"%s",\n' % (vtab, v)
        iargs += '%sdouble %s,\n' % (tab, v)
        hargs += '%sdouble %s,\n' % (htab, v)
        inpvars += '%sinputVars[%d]\t= %s;\n' % (ptab, ii, v)
        
        tab  = TAB
        vtab = VTAB
        htab = '// ' + HTAB
        ptab = '    '

    ivars = ivars[:-2]
    iargs = iargs[:-2]
    hargs = hargs[:-2]
    inpvars = inpvars[:-1]

    names  =  \
          {'code':    code,
           'time' :   ctime(),
           'ntrees0': ntrees0,
           'ntrees':  ntrees,
           'ivars':   ivars,
           'hargs' :  hargs,
           'iargs' :  iargs,
           'inpvars': inpvars,
           'funcname':funcname,
           'ninputs': len(inputvars),
           'classname': classname}

    record = '''// -------------------------------------------------------------------------
// double mvd(%(hargs)s);
//      :    :
// To build lib%(funcname)s.so do
//   make -f %(funcname)s_makefile
//
// To call from C++
//   gSystem->Load("lib%(funcname)s.so");
//      :    :
//   %(funcname)s mvd;
//   double D = mvd(...);
//
// Fromm Python
//   gSystem.Load("lib%(funcname)s.so");
//      :    :
//   mvd = %(funcname)s()
//   D = mvd(...)
//
// created: %(time)s
// -------------------------------------------------------------------------
// 
//
%(code)s
// Instantiate an  object
std::string ivars[] = {%(ivars)s};
std::vector<std::string> iivars(ivars, ivars + %(ninputs)d);
};


// -------------------------------------------------------------------------

struct %(funcname)s : public __%(funcname)s::%(classname)s
{
  %(funcname)s() : __%(funcname)s::%(classname)s(__%(funcname)s::iivars) {}
  ~%(funcname)s() {}

  double operator()(std::vector<double>& inputVars%(ntrees0)s)
  {
    return GetMvaValue(inputVars%(ntrees)s);
  }

  double operator()(%(iargs)s%(ntrees0)s)
  {
    std::vector<double> inputVars(%(ninputs)d);
  %(inpvars)s
    return GetMvaValue(inputVars%(ntrees)s);
  }
};
    ''' % names
    print
    print '==> creating file: %s' % outfilename
    open(outfilename, 'w').write(record)

    # --------------------------------------------------------------------------
    # write linkdef
    # --------------------------------------------------------------------------
    record = '''
#ifdef __CINT__
#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;
#pragma link C++ class std::pair<double, std::string>+;
#pragma link C++ class std::vector<std::pair<double, std::string> >+;
#pragma link C++ class __%(funcname)s::%(classname)s+;
#pragma link C++ class %(funcname)s+;
#endif
''' % names
    outfilename = '%s_linkdef.h' % funcname
    print '==> creating file: %s' % outfilename    
    open(outfilename, 'w').write(record)

    # --------------------------------------------------------------------------
    # write makefile
    # --------------------------------------------------------------------------
    record = '''# ------------------------------------------------------------------------------
# build lib%(funcname)s.so
# created: %(time)s by writeTMVA.py
# ------------------------------------------------------------------------------
AT      := @
CXXFLAGS:= $(shell root-config --cflags)
LDFLAGS	:= $(shell root-config --ldflags)
LIBS	:= $(shell root-config --libs)

lib%(funcname)s.so:	%(funcname)s_dictionary.cxx
\t$(AT)echo "building library $@"
\t$(AT)g++ -shared -o $@  $(LDFLAGS) $(LIBS) $(CXXFLAGS) $^

%(funcname)s_dictionary.cxx: %(funcname)s.cc %(funcname)s_linkdef.h
\t$(AT)echo "building dictionary file $@"
\t$(AT)rootcint -f $@ -c $(CXXFLAGS) $+

clean:
\trm -rf %(funcname)s_dictionary.cxx lib%(funcname)s.so %(funcname)s*.pcm

nuke:
\trm -rf %(funcname)s_* %(funcname)s.cc
''' % names
    outfilename = '%s_makefile' % funcname
    print '==> creating file: %s' % outfilename    
    open(outfilename, 'w').write(record)

    print '''
Do
   make -f %(funcname)s_makefile

to build lib%(funcname)s.so
''' % names
    
#-------------------------------------------------------------------------------
try:
    main()
except KeyboardInterrupt:
    print "\n\nciao!\n"
