import sys,os
from array import array
import argparse
import numpy as np
import uproot
import pandas as pd
import modules.load_data as load_data
import modules.get_ids as get_ids
from root_pandas import to_root
from tqdm import tqdm
import gc
import functools
print = functools.partial(print, flush=True)
import psutil
process = psutil.Process(os.getpid())
print(str(float(process.memory_info().rss)/1000000))  # in bytes 

parser = argparse.ArgumentParser()

parser.add_argument('-f', '--file', dest = 'file',
                    default=None, help="file")
parser.add_argument('-y', '--year', dest = 'year',
                    default=2017, help="year")
parser.add_argument('-e', '--extra', dest = 'extra',
                    default=None, help="extraCalib file ")
parser.add_argument('-d', '--debug', dest= 'debug', default = False, action = 'store_true')
args =parser.parse_args()

branches = ['xSeedSC','ySeedSC',
        'noiseSeedSC', 
        'eventTime','runNumber']

branches_extra = ['XRecHitSCEle1','XRecHitSCEle2',
                  'YRecHitSCEle1','YRecHitSCEle2',
                  'ZRecHitSCEle1','ZRecHitSCEle2']


branches_todrop = []

print("@@@ Loading files...")
file = args.file
file_extra = args.extra
if args.debug:
    file = "/drf/projets/cms/ca262531/ecalelf/ntuples/13TeV/ALCARERECO/PromptReco2017_103X_EtaScaleupdatedSCregressionV3/DoubleEG-Run2017B-ZSkim-Prompt-v1/297046-297723/294927-306462_Prompt_v1/pedNoise/DoubleEG-Run2017B-ZSkim-Prompt-v1-297046-297723.root"
    file_extra = "/drf/projets/cms/ca262531/ecalelf/ntuples/13TeV/ALCARERECO/PromptReco2017_103X_EtaScaleupdatedSCregressionV3/DoubleEG-Run2017B-ZSkim-Prompt-v1/297046-297723/294927-306462_Prompt_v1/pedNoise/extraCalibTree-DoubleEG-Run2017B-ZSkim-Prompt-v1-297046-297723.root"

if not os.path.isfile(file):
    print ("Could not find file:", file)
    sys.exit()
if not os.path.isfile(file_extra):
    print ("Could not find file:", file_extra)
    sys.exit()

df = load_data.load_file(file, "selected", branches)
branches_split = ["xSeedSC","ySeedSC","noiseSeedSC"]
for br in branches_split:
    if br+"[1]" in df.columns:
        df[[br+'1', br+'2']] = df[[br+'[0]',br+'[1]']]
        branches_todrop.append(br+'1')
        branches_todrop.append(br+'2')
        df = df.drop(columns = [br+'[0]',br+'[1]', br+'[2]'] )

initial_size = df.shape[0]
print(str(float(process.memory_info().rss)/1000000))  #
#df_extra = load_data.load_file(file_extra, "extraCalibTree", branches_extra) # taking only iX, iY, iZ of first and second by energy
#df_extra1 = df_extra.stack().str[0].unstack().fillna(-999).astype("int")
#df_extra1 = df_extra1.drop(columns = ['XRecHitSCEle1','XRecHitSCEle2','YRecHitSCEle1','YRecHitSCEle2'])
#df_extra1.columns = ["zSeedSC1","zSeedSC2"]
#df_extra2 = df_extra.stack().str[1].unstack().fillna(-999).astype("int")
#df_extra2.columns = ["xSecondToSeedSC1","xSecondToSeedSC2","ySecondToSeedSC1","ySecondToSeedSC2","zSecondToSeedSC1","zSecondToSeedSC2"]

extra1_chunk_list = []
extra2_chunk_list = []
for df_extra_chunk in tqdm(uproot.pandas.iterate(file_extra, "extraCalibTree", branches_extra,
                                entrysteps=10000, flatten = False)):
    df_extra1_chunk = df_extra_chunk.stack().str[0].unstack().fillna(-999).astype("int").drop(columns = ['XRecHitSCEle1','XRecHitSCEle2','YRecHitSCEle1','YRecHitSCEle2'])
    df_extra1_chunk.columns = ["zSeedSC1","zSeedSC2"]
    df_extra2_chunk = df_extra_chunk.stack().str[1].unstack().fillna(-999).astype("int")
    df_extra2_chunk.columns = ["xSecondToSeedSC1","xSecondToSeedSC2","ySecondToSeedSC1","ySecondToSeedSC2","zSecondToSeedSC1","zSecondToSeedSC2"]
    del df_extra_chunk
    gc.collect()
    df_extra_chunk = pd.DataFrame()
    extra1_chunk_list.append(df_extra1_chunk)
    extra2_chunk_list.append(df_extra2_chunk)
df_extra1 = pd.concat(extra1_chunk_list)
df_extra2 = pd.concat(extra2_chunk_list)
del extra1_chunk_list, extra2_chunk_list
df = pd.concat([df, df_extra1, df_extra2], axis=1) 
del df_extra1, df_extra2
gc.collect()
df_extra1 = pd.DataFrame()
df_extra2 = pd.DataFrame()
print(process.memory_info().rss)  #
#-------------------
print("@@@ Loading fill lumi table...")

lumi_file = "/drf/projets/cms/ca262531/fill_lumi/lumi_Run1_Run2_unixTime.dat"
df_lumi_chunks = pd.read_csv(lumi_file, sep='\s+', usecols = [0, 1, 3, 6], comment = '#', chunksize=5000)
lumi_chunk_list = []
for df_lumi_chunk in tqdm(df_lumi_chunks):
    df_lumi_chunk[["Run","Fill"]] = df_lumi_chunk["Run:Fill"].str.split(":", n = 1, expand = True) 
    df_lumi_chunk["LS"] = df_lumi_chunk["LS"].str.split(":", n = 1, expand = True)[0]
    df_lumi_chunk = df_lumi_chunk[(df_lumi_chunk["Beam_Status"]=="STABLE_BEAMS")].drop(columns = ["Beam_Status","Run:Fill"])
    lumi_chunk_list.append(df_lumi_chunk)
# concat the list into dataframe 
df_lumi = pd.concat(lumi_chunk_list)
del lumi_chunk_list
group = df_lumi.groupby("Run").agg({'Recorded(/ub)':'sum', 'LS':'count', 'Fill':'first'}).reset_index()
df['Fill'] = df['runNumber'].map(group.astype('int').set_index('Run')['Fill'])
df['LumiSections'] = df['runNumber'].map(group.astype('int').set_index('Run')['LS'])
df['RecordedLumi'] = df['runNumber'].map(group.astype({'Run':'int'}).set_index('Run')['Recorded(/ub)'])
df['LumiInst']     = df['RecordedLumi']/23000

print(str(float(process.memory_info().rss)/1000000))  #
del df_lumi, group

gc.collect()
df_lumi = pd.DataFrame()
group = pd.DataFrame()
#---------------------
print("before appending:" , str(process.memory_info().rss/1000000))  #
print("@@@ Appending DetIDs and geometric/electronic elements...")

df = get_ids.appendIdxs(df, "1")
df = get_ids.appendIdxs(df, "2")
df = get_ids.appendIdxs(df, "1", "SecondToSeed")
df = get_ids.appendIdxs(df, "2", "SecondToSeed")    

print("after appending:", str(float(process.memory_info().rss)/1000000))  #

print("@@@ Loading IOVs: EcalPedestals (Run 2 UL)")
era = file.split("Run"+str(args.year))[1][0]
print(process.memory_info().rss)  #
print("@@@ Run"+str(args.year)+str(era))
dump_file = "/drf/projets/cms/ca262531/ECALconditions_dumps/EcalPedestalsRun"+str(args.year)+str(era)+".dat"

dump_chunk_list = []  # append each chunk df here 
df_dump_chunks = pd.read_csv(dump_file, chunksize=10000, sep='\s+',  header=None, usecols = [4, 5, 7], names = ["noise","begin", "DetID"])
for df_dump_chunk in tqdm(df_dump_chunks):  
    df_dump_chunk["begin"] = (df_dump_chunk["begin"].values  >> 32)
    df_dump_chunk = df_dump_chunk.astype({'noise':'float', 'DetID':'int32', 'begin':'int32'})
    dump_chunk_list.append(df_dump_chunk)
# concat the list into dataframe 
df_dump = pd.concat(dump_chunk_list)
del dump_chunk_list

df_dump["end"] = df_dump["begin"].shift(-1)
df_dump.loc[max(df_dump.index), ["end"]] = 1591695307
df_dump.astype({'end':'int32'})
df_red = df_dump[["begin","end"]].drop_duplicates()
gc.collect()

print(str(float(process.memory_info().rss)/1000000))  #
#---------------------

print ("@@@ Matching IOVs...")
print(str(float(process.memory_info().rss)/1000000))

#i, j = np.where((df.eventTime.values[:, None] >= df_red.begin.values) & (df.eventTime.values[:, None] < df_red.end.values))

chunk_list = []
for g, df_chunk in df.groupby(np.arange(len(df)) // 50000):
    
    i, j = np.where((df_chunk.eventTime.values[:, None] >= df_red.begin.values) & (df_chunk.eventTime.values[:, None] < df_red.end.values))
    df_chunk = pd.DataFrame(
        np.column_stack([df_chunk.values[i], df_red.values[j]]),
        columns=df_chunk.columns.append(df_red.columns)
    )
    chunk_list.append(df_chunk)
    del i, j
    gc.collect()

df = pd.concat(chunk_list)
del chunk_list

print("added begin end", str(float(process.memory_info().rss)/1000000))

print(df.shape[0])
del df_red
gc.collect()
df_red = pd.DataFrame()
print(process.memory_info().rss)  #
print ("@@@ Mapping Ecal pedestals by time and crystal...")
chunk_list = []
for g, df_chunk in df.groupby(np.arange(len(df)) // (initial_size/20)):
    print ("@@@ Going over chunks...", str(float(process.memory_info().rss)/1000000))
    print(df_chunk.shape[0])
    df_chunk['noiseSeedSC1_GT']        = df_chunk.set_index(['EcalDetIDSeedSC1','begin']).index.map((df_dump[['DetID','noise','begin']].set_index(['DetID','begin'])['noise'])).astype('float')
    df_chunk['noiseSeedSC2_GT']        = df_chunk.set_index(['EcalDetIDSeedSC2','begin']).index.map((df_dump[['DetID','noise','begin']].set_index(['DetID','begin'])['noise'])).astype('float')
    df_chunk['noiseSecondToSeedSC1_GT'] = df_chunk.set_index(['EcalDetIDSecondToSeedSC1','begin']).index.map((df_dump[['DetID','noise','begin']].set_index(['DetID','begin'])['noise'])).astype('float')
    df_chunk['noiseSecondToSeedSC2_GT'] = df_chunk.set_index(['EcalDetIDSecondToSeedSC2','begin']).index.map((df_dump[['DetID','noise','begin']].set_index(['DetID','begin'])['noise'])).astype('float')
    chunk_list.append(df_chunk)
df = pd.concat(chunk_list)
del chunk_list
print(df.shape[0])

del df_dump
gc.collect()

df_dump = pd.DataFrame()

#don't save the quantities that exist already in the original tree
df = df.drop(columns = branches_todrop)
gc.collect()

outfile_name = file.replace(".root", "_extra.root")
print("@@@ Saving output file ", outfile_name)
df.to_root(outfile_name, key = "extended", mode='w') # recreate mode

final_size = df.shape[0]
if initial_size > final_size:
    print("HEADS UP! final size is smaller than initial size")
    print("initial ", str(initial_size))
    print("final   ", str(final_size))
