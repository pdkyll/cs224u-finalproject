
#!/usr/bin/env python
# Cayman Simpson (cayman@stanford.edu), Harley Sugarman (harleys@stanford.edu), Angelica Perez (pereza77@stanford.edu)
# CS224U, Created: 3 May 2015
# file: testaker.py

# =====================================================================================================================================================
# =====================================================================================================================================================
# ====================================================================== IMPORTS ======================================================================
# =====================================================================================================================================================
# =====================================================================================================================================================


# =====================================================================================================================================================
# =====================================================================================================================================================
# ================================================================= UTILITY FUNCTIONS =================================================================
# =====================================================================================================================================================
# =====================================================================================================================================================

# A command line progress bar that accepts an integer from 1-100
def update_progress(progress):
    sys.stdout.write('\r');
    sys.stdout.write('[{0}>{1}] {2}%'.format('='*int(progress/10), ' '*(10 - int(progress/10)), progress));
    sys.stdout.flush();

# Reads a file and returns the text contents
def readFile(filename):
    with open(filename) as f: return f.read();

# Throws an error.
#   First param: String that contains error/notification
#   Second param: Whether to halt program execution or not.
def error(msg, shouldExit):
    print '\033[91m' + msg + '\033[0m';
    if(shouldExit): sys.exit();

# Prints a success (in green).
def printSuccess(message):
    print '\n\033[92m' + str(message) + '\033[0m\n';

# Returns a list of all filenames that are recursively found down a path.
#   First param: String of initial directory to start searching
#   Second param (optional): A filter function that filters the files found. Default returns all files.
def getRecursiveFiles(path, filter_fn=lambda x: True):
    paths = [path]
    files = [];
    try:
        while(len(paths) > 0):
            path = paths[0] if paths[0][-1] != "/" else paths[0][:-1];
            children = [f for f in listdir(paths[0])];
            for child in children:
                if not isfile(join(path,child)) and "." not in f: paths.append(join(path,child));
                elif isfile(join(path,child)): files.append(join(path,child));
                paths = paths[1:]; #remove te path we just looked at
        return filter(filter_fn, files);
    except:
        error(path + " is not a directory. Exiting...", True);

# =====================================================================================================================================================
# =====================================================================================================================================================
# ================================================================= DISTANCE METRICS ==================================================================
# =====================================================================================================================================================
# =====================================================================================================================================================

def kldist(p,q):
    return reduce(lambda soFar,i: soFar + p[i]*np.log(p[i]/q[i]), xrange(len(p)), 0);

def jsd(p,q):
    p = map(lambda u: u/sum(p), p);
    q = map(lambda v: v/sum(q), q);
    m = .5*np.add(p,q);
    return np.sqrt(.5*kldist(p,m) + .5*kldist(q,m))

def L2(u,v):
    return reduce(lambda soFar,i: soFar + (u[i]-v[i])*(u[i]-v[i]), range(len(u)), 0);

def cosine(u, v):
    return scipy.spatial.distance.cosine(u, v)

# distributed reps has: cosine, L1 (euclidean), jaccard

# =====================================================================================================================================================
# =====================================================================================================================================================
# ================================================================== MAIN CODE BASE ===================================================================
# =====================================================================================================================================================
# =====================================================================================================================================================

#-1 is no guess, [(ourguess_int, gold_int)]
def rand_baseline(passages):
    guesses = [];
    for passage in passages:
        for question in passage.questions:
            guesses.append( (random.randint(0,4),question.correctAnswer) );
    return guesses;

def nnBaseline(passages, glove, distfunc, threshold=None):
    guesses = [];
    for passage in passages:
        for question in passage.questions:
            targetword = re.findall("[\xe2\x80\x9c\u2019\"\']([A-Za-z\s]+)[\xe2\x80\x9c\u2019\"\']", question.text)[0]; # Doesnt work
            targetvec = glove.getVec(targetword);

            # Glove does not have the target word in its vocabulary
            if(targetvec == None):
                error("Glove does not have \"" + targetword + "\" in its vocabulary", False);
                continue;

            mindist = 10e100;
            ind = -1;
            for i,answer in enumerate(question.answers):

                # Glove does not have the answer in its vocabulary
                if(glove.getVec(answer) == None):
                    error("Glove does not have the answer \"" + answer + "\" in its vocabulary", False);
                    continue;

                if( mindist > distfunc(glove.getVec(answer), targetvec) ):
                    print "Distance between " + str(answer) + " and " + str(targetword) + " is: "
                    print str(distfunc(glove.getVec(answer), targetvec));
                    ind = i;
                    mindist = distfunc(glove.getVec(answer), targetvec);
            if threshold is not None:
                if mindist <= threshold:
                    guesses.append( (ind, question.correctAnswer) );
                else:
                    guesses.append( (-1, question.correctAnswer) );
            else:
                guesses.append( (ind, question.correctAnswer) );
    return guesses;

def addVec(words, glove):
    targetvec = glove.getVec(words[0]);
    if(targetvec == None): error("Glove does not have \"" + words[0] + "\" in its vocabulary. Producing bug here.", False); # Will produce bug if first word is not in vocab

    for word in words[1:]:
        wordvec = glove.getVec(word);
        if(wordvec != None):
            targetvec = map(lambda i: targetvec[i] + wordvec[i], xrange(len(targetvec)));
        else: error("Glove does not have \"" + word + "\" in its vocabulary", False);
    return targetvec;

def getAverageVec(words, glove):
    targetvec = glove.getVec(words[0]);
    if(targetvec == None): error("Glove does not have \"" + words[0] + "\" in its vocabulary", False);

    count = 0;
    for word in words[1:]:
        wordvec = glove.getVec(word);
        if(wordvec != None):
            count += 1;
            targetvec = map(lambda i: targetvec[i] + wordvec[i], xrange(len(targetvec)));
            
        else: error("Glove does not have \"" + word + "\" in its vocabulary", False);

    targetvec = map(lambda x: x/count, targetvec);
    return targetvec

def sentenceBaseline(passages, glove, distfunc, threshold):
    guesses = [];
    for passage in passages:
        for question in passage.questions:
            targetline = int(re.findall("[0-9]+", question.text)[0]) - 1; # Lines are 1 indexed

            sentence = passage.text.split("\n")[int(targetline)];
            sentence = re.split("[^A-Za-z0-9]", sentence);
            sentence = filter(lambda x: len(x) > 0, sentence);
            sentence = map(lambda x: x.strip().lower(), sentence);

            targetvec = glove.getVec(sentence[0]);
            if(targetvec == None):
                error("Glove does not have \"" + sentence[0] + "\" in its vocabulary", False);
                continue;

            targetvec = getAverageVec(sentence, glove);

            mindist = 10e100;
            ind = -1;
            for i,answer in enumerate(question.answers):
                vec = glove.getVec(answer);

                # Two word answer, adding the vector
                if(" " in answer): vec = addVec(answer.split(" "), glove);

                # Glove straight up does not have the answer in its vocabulary
                if(vec == None):
                    error("Glove does not have the answer \"" + answer + "\" in its vocabulary", False);
                    continue;

                if( distfunc(vec, targetvec) < mindist and distfunc(vec, targetvec) < threshold):
                    ind = i;
                    mindist = distfunc(vec, targetvec);
            guesses.append( (ind, question.correctAnswer) );
    return guesses;

#returns a matrix of word-document frequencies
def createWordDocMatrix(passages, data_passages):
    allWords = []; #to hold all answer words and words contained in all target senteces
    for passage in passages:
        for question in passage.questions:
            targetline = int(re.findall("[0-9]+", question.text)[0]) - 1; # Lines are 1 indexed

            sentence = passage.text.split("\n")[int(targetline)];
            sentence = re.split("[^A-Za-z0-9]", sentence);
            sentence = filter(lambda x: len(x) > 0, sentence);
            sentence = map(lambda x: x.strip().lower(), sentence);

            for word in sentence:
                if word not in allWords:
                    allWords.append(word);

            for a in question.answers:
                if a not in allWords:
                    allWords.append(a);


    matrix = np.zeros((len(allWords), len(data_passages)));
    for i,dp in enumerate(data_passages):
        words = [];
        words = re.split("[^A-Za-z0-9]", dp.text);
        words = filter(lambda x: len(x) > 0, words);
        words = map(lambda x: x.strip().lower(), words);
        wordCounts = Counter(words);

        for j,w in enumerate(allWords):
            if w in words:
                matrix[j][i] = wordCounts[w];
            
    return matrix, allWords

#computes the sum of the glove vectors of all elements in words
def getSumVec(words, glove):
    targetvec = glove.getVec(words[0]);
    if(targetvec == None): error("Glove does not have \"" + words[0] + "\" in its vocabulary", False);

    count = 0;
    for word in words[1:]:
        wordvec = glove.getVec(word);
        if(wordvec != None):
            count += 1;
            targetvec = map(lambda i: targetvec[i] + wordvec[i], xrange(len(targetvec)));
            
        else: error("Glove does not have \"" + word + "\" in its vocabulary", False);

    return targetvec

import operator

#returns a list of the five words in sentence with the highest tfidf scores
def findTopFive(sentence, tfidf, allWords):
    d = defaultdict(float);
    for word in sentence:
        i = allWords.index(word);
        d[word] = tfidf[i] ;
    sorted_d = sorted(d.items(), key=operator.itemgetter(1));

    words = [];
    values = [];
    for key,val in sorted_d:
        words.append(key);
        values.append(val);

    return words[-5:];

#finds the average of each word's non-zero tfidf values
def computeTFIDFArray(tfidf_mat):
    tfidf_array = [];
    for i,row in enumerate(tfidf_mat):
        count = 0.0;
        rowSum = 0.0;
        for val in row:
            if val > 0.0:
                count += 1.0;
                rowSum += val;

        if count == 0.0:
            tfidf_array.append(0.0)
        else:
            tfidf_array.append(rowSum/count);

    return tfidf_array;

#uses additional data passages to compute tfidf
def sentenceTFIDF(passages, data_passages_file, glove, distfunc, threshold):
    guesses = [];
    data_passages = loadPassages(data_passages_file);
    freqMatrix, allWords = createWordDocMatrix(passages, data_passages);

    dis_mat = disambiguate(mat=freqMatrix, rownames=allWords);
    print neighbors(mat=dis_mat[0], word='fair_0', rownames=dis_mat[1]);
    


    tfidf_mat = tfidf(mat=freqMatrix)[0];
    tfidf_array = computeTFIDFArray(tfidf_mat);

    for passage in passages:
        for question in passage.questions:
            targetline = int(re.findall("[0-9]+", question.text)[0]) - 1; # Lines are 1 indexed

            sentence = passage.text.split("\n")[int(targetline)];
            sentence = re.split("[^A-Za-z0-9]", sentence);
            sentence = filter(lambda x: len(x) > 0, sentence);
            sentence = map(lambda x: x.strip().lower(), sentence);

            topFive = findTopFive(sentence, tfidf_array, allWords);

            targetvec = glove.getVec(topFive[0]);
            if(targetvec == None):
                error("Glove does not have \"" + topFive[0] + "\" in its vocabulary", False);
                continue;


            targetvec = getSumVec(topFive, glove);

            mindist = 10e100;
            ind = -1;
            for i,answer in enumerate(question.answers):
                vec = glove.getVec(answer);

                # Two word answer, adding the vector
                if(" " in answer): vec = addVec(answer.split(" "), glove);

                # Glove straight up does not have the answer in its vocabulary
                if(vec == None):
                    error("Glove does not have the answer \"" + answer + "\" in its vocabulary", False);
                    continue;

                if( distfunc(vec, targetvec) < mindist and distfunc(vec, targetvec) < threshold):
                    ind = i;
                    mindist = distfunc(vec, targetvec);
            guesses.append( (ind, question.correctAnswer) );
    return guesses;


# Loads all passages in file.
def loadPassages(path):
    files = getRecursiveFiles(path, lambda x: x[x.rfind("/") + 1] != "." and ".txt" in x and x[-1] != '~');
    return [Passage(filename) for filename in files];

# Main method
def main(f, o, g, v):
    if(v): print "Loading passages...";
    passages = loadPassages(f);

    if(v): print "Loading glove vectors...";
    glove = Glove(g, delimiter=" ", header=False, quoting=csv.QUOTE_NONE);

    if(v): print "Finished loading all data!";

    # random_model = rand_baseline(passages);
    #nnBaseline_model = nnBaseline(passages, glove, cosine, 0.7);
    model = sentenceTFIDF(passages, "../data/data_passages", glove, cosine, 0.45)

    score = score_model(model, verbose=True)



# =====================================================================================================================================================
# =====================================================================================================================================================
# =============================================================== COMMAND LINE REFERENCE ==============================================================
# =====================================================================================================================================================
# =====================================================================================================================================================

# Command Line Reference:
#   Example call: python testaker.py -f "../data/passages" -v -c column_num -o "../output.txt"
#   1) -v: if you want this program to be verbose
#   2) -o: if you want this program to output results to a file (defaults to printing to console)
#   3) -f: filename or path flag pointing to data (necessary)
#   4) -g: filename for glove vectors, default "../data/glove_vectors/glove.6B.50d.txt"
if __name__ == "__main__":

    # Preliminary loading to get arguments
    import sys
    import time
    from collections import Counter

    start = time.time();
    args = sys.argv[1:];

    v = reduce(lambda a,d: a or d== "-v", args, False);
    if(v): print "\nImporting modules..."

    f = "";
    o = "";
    g = "../data/glove_vectors/glove.6B.50d.txt";

    # Get command lime arguments
    for i, arg in enumerate(args):
        if(arg == "-f"): # extract the filename argument
            f = args[i+1];
        elif(arg == "-o"): # extract the output filename argument
            o = args[i+1];
        elif(arg == "-g"):
            g = args[i+1];

    # Report error if called the wrong way
    if(f == ""):
        error("You must use the -f flag to specify where to find that data.\n   1) -v: if you want this program to be verbose\n   2) -o: if you want this program to output results to a file (defaults to printing to console)\n   3) -f: filename or path flag pointing to data (necessary)\n    4) -g: path to glove vector file (defaults to '../data/glove_vectors/glove.6B.50d.txt'", True)


    # Loading Modules
    import scipy
    from nltk.tag.stanford import POSTagger
    from distributedwordreps import *
    import NaiveBayes as nb
    import time
    from os import listdir
    from os.path import isfile, join
    import random
    import re
    from Passage import *
    from Question import *
    from Glove import *
    from scoring import score_model

    if(v): print "All modules successfully loaded in " + str(int(time.time() - start)) +  " seconds!"

    # Main Method
    main(f, o, g, v);

    # Finished Testaker execution
    if(v): printSuccess("Program successfully finished and exited in " + str(int(time.time() - start)) +  " seconds!");
    sys.exit();

# =====================================================================================================================================================
# =====================================================================================================================================================
# =================================================================== EXAMPLE CALLS ===================================================================
# =====================================================================================================================================================
# =====================================================================================================================================================


"""
Example call of POSTagger:
======================================================
tagger = POSTagger(
        'stanford-postagger/models/french.tagger', 
        'stanford-postagger/stanford-postagger.jar',
        'utf-8'
    );

tagger.tag_sents(array_of_string_sentences);


Example call of NaiveBayes:
======================================================
classifier = nb.NaiveBayes();
nb.addExamples(["good","good","ok","bad"],["pos","pos","pos","neg"]);
print nb.classify("good");

Example call of Passages and Questions
======================================================
Passage(filename) <= creates questions and stores them in member
passage.text = "passage text"
passage.questions = [Question Object, Question Object]

Question(text) <= constructor, created within Passage constructor, text automatically passed
Question.text = "question prompt text"
question.answers = ["answer #0", "answer #1"]
question.correctAnswer = int_of_correct_answer <= corresponds with index of answers

Example call of Glove Module
======================================================
glove = Glove(filename);
print glove.getVec("and"); # <= prints out glove vector for that word, or None if word not in vocab
print glove.getVocab(); # <= returns an array of all the words the glove vectors have
"""





