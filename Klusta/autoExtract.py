import findNewRecordings
import RHDtoDATprbPRM
import os
import datetime

def autoExtract():
	workingPaths = findNewRecordings.findNewRecordings()
	for path, basename in workingPaths:
		print(path, basename)
		if not(os.path.isfile(path+'/'+basename+'.prm')):
			RHDtoDATprbPRM.RHDtoDATprbPRM(path, basename, 'A1x32-Poly2-5mm-50s-177-A32.prb') # 'ASSY-37W-DBC11A-intan.prb' this is Brendan's edge probe from Cambridge Neurotech
			# hard coded the poly2 probe for now. This could be improved in the future: 'A1x32-Poly2-5mm-50s-177-A32.prb'
			dt = datetime.datetime.now()
			with open('C:\\DATA\\autoClusterLogs\\log'+dt.strftime('%Y%m%d')+'.txt','a') as f2:
				f2.write('New clustering performed.\n')
		else:
			print('already extracted')
			dt = datetime.datetime.now()
			with open('C:\\DATA\\autoClusterLogs\\log'+dt.strftime('%Y%m%d')+'.txt','a') as f2:
				f2.write('Extraction was performed previously.\n')

def main():
	autoExtract()

if __name__ == '__main__':
	main()	