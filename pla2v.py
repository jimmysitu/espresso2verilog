#! /usr/bin/python
import sys
import re
import os
import threading


class plaInfo():
    def __init__(self, inList, outList, caseHash, optType):
        self.i = []
        self.o = []
        self.opt = optType
        self.casex = caseHash
        for m in inList:
            result = re.search(r'(\w+)\[(\d+):(\d+)\]', m)
            inName = result.group(1)
            inUpper = int(result.group(2))
            inLower = int(result.group(3))
            if inUpper >= inLower:
                for n in range(inUpper, inLower-1, -1):
                    self.i.append(inName+r'['+str(n)+r']')
            else:
                for n in range(inUpper, inLower-1, 1):
                    self.i.append(inName+r'['+str(n)+r']')

        for m in outList:
            result  = re.search(r'(\w+)\[(\d+):(\d+)\]', m)
            outName = result.group(1)
            outUpper = int(result.group(2))
            outLower = int(result.group(3))
            if outUpper >= outLower:
                for n in range(outUpper, outLower-1, -1):
                    self.o.append(outName+r'['+str(n)+r']')
            else:
                for n in range(outUpper, outLower-1, 1):
                    self.o.append(outName+r'['+str(n)+r']')

    # Print truth table to tFile, and call espresso to minimize it
    # Result stores to plaStr
    def genPla(self):
        tFile = open('gen.pla', 'w')
        print >>tFile, "# This is a espresso optimized file\n"
        print >>tFile, ".i %d" % len(self.i)
        print >>tFile, ".o %d\n" % len(self.o)
        print >>tFile, ".ilb %s" % (' '.join(self.i))
        print >>tFile, ".ob %s\n" % (' '.join(self.o))
        print >>tFile, ".type %s\n" % self.opt
        for k in self.casex.keys():
            inStr = re.sub(r'_', r'', k)
            inStr = re.sub(r'x', r'-', inStr)
            outStr= re.sub(r'^0b', r'', str(bin(self.casex[k])))
            outStr= '0' * (len(self.o)-len(outStr)) + outStr
            print >>tFile, "%s %s" % (inStr, outStr)
        print >>tFile, ".e\n"
        tFile.close()
        os.system('./espresso gen.pla > plaFile.pla')

    def checkThread(self, genStr, casexList, thrNum):
        log = open("thr%s.log" % thrNum, 'w')
        for v in casexList:
            regexStr = re.sub(r'_', r'', v)
            regexStr = re.sub(r'x', r'.', regexStr) + r' [01-]+'
            #print >>log, regexStr
            result = re.findall(regexStr, genStr)
            if len(result) > 1:
                print >>log, 'Error:'
                print >>log, v
                print >>log, '\n'.join(result)
        log.close()
        return

    def checkGenPla(self, genFile):
        genStr = open(genFile).read()
        #print >>sys.stderr, genStr
        casexList = self.casex.keys()
        for i in range(0, 4):
            caseStart = (len(casexList)/4+1) * i
            caseEnd   = (len(casexList)/4+1) * (i+1) - 1
            subList = casexList[caseStart: caseEnd] if i<3 else casexList[caseStart:]
            t = threading.Thread(target=self.checkThread, args=(genStr,subList,i))
            t.start()

    # Convert PLA to verilog boolean expression
    # Save return a hash, output port is key, expression is value
    def pla2vExpr(self):
        self.genPla()
        tFile = open('plaFile.pla', 'r')

        # Read PLA, translate it to verilog style
        exprHash = {}
        line = tFile.readline()
        while line:
            result = re.search(r'([01-]+) ([01-]+)', line)
            if result:
                inputValue = list(result.group(1))
                outputValue = list(result.group(2))
                for p in range(len(outputValue)):
                    if outputValue[p] == '1':
                        tmpList = []
                        for q in range(len(inputValue)):
                            if inputValue[q] == '1':
                                tmpList.append(self.i[q])
                            elif inputValue[q] == '0':
                                tmpList.append('~'+self.i[q])
                        # Check and tie output to 1'b1 if all input is DC
                        if len(tmpList) == 0:
                            tmpList.append("1'b1")
                        try:
                            exprHash[self.o[p]].append(' & '.join(tmpList))
                        except:
                            exprHash.update({self.o[p]:[]})
                            exprHash[self.o[p]].append(' & '.join(tmpList))
            line = tFile.readline()
        tFile.close()

        # Check if any output port undriven
        for k in self.o:
            try:
                exprHash[k]
            except:
                exprHash.update({k: ["1'b0"]})

        for k in exprHash.keys():
            exprHash.update({k: "\n | ".join(exprHash[k])})

        return exprHash

