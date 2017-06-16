import findNewRecordings
import RHDtoDATprbPRM
import os
import subprocess

def autoCluster():
	origDir = os.getcwd()
	workingPaths = findNewRecordings.findNewRecordings()
	
	f = open('C:\\users\\Alan\\Documents\\Github\\kwik-tools\\tempBAT.bat','w+')
	#f.write('@echo off\n')
	f.write('title temp bat for clustering\n')
	f.write('Z:\n') # change to server drive, after which changing directory cd will work.
	f.write('source activate phy\n')
	
	for path, basename in workingPaths:
		if not(os.path.isfile(path+'/'+basename+'.kwik')):
			print(path)
			#sendString = 'cd '+str(path)+';ls'#activate phy; klusta '+str(basename)+'.prm'
			#print(sendString)
			#subprocess.call(['activate phy'],shell=True, cwd=path) #,'activate phy','klusta '+basename+'.prm'],shell=True)
			f.write('cd '+path+'\n')
			f.write('klusta '+basename+'.prm\n')
			
	f.close()
	
	p = subprocess.Popen('C:\\users\\Alan\\Documents\\Github\\kwik-tools\\tempBAT.bat',shell=True)
	stdout, stderr = p.communicate()

def main():
	autoCluster()

if __name__ == '__main__':
	main()	