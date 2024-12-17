Flexibility_RT_Eta_v5_test4.py

Input files: 

	UCSD_AllSites_Merge_Eta_20210504_20230129_v3.csv
	Driver_Table.csv
	2022_PerfectSessionkWh_PerfectNumbEV_PerfectatArrival_MonthlyTh_Eta_v5_test4.csv
	PowerFlex input for EV statistics to be plugged into master sheet.csv

	daily LMP files (can be found in folder '2024_RO3.4_Data')'
	

Output files:

	2022_PerfectSessionkWh_PerfectNumbEV_PerfectatArrival_MonthlyTh_Eta_v5_test4.csv
	Plots and sessionkWh files are optinal


This optimization model includes 2 layers:

	Day-ahead optimization

	Real-time optimization (realization, optimization, and execution)


The available forecast options:
	Fc_SessionkWh = 'PerfectSessionkWh' #'PersistenceSessionkWh'
	Fc_NumbEV = 	'PerfectNumbEV'     #'PersistenceNumbEV'
	Fc_AtArrival = 	'PerfectatArrival'  #'MLatArrival'


Available cases:
	Cases = ['Base', 'Case1']
	#always run both the base case (no demand reduction) and the case with service reduction


Version of packages 
	python 3.10.4
	numpy 1.23.1
	pandas 1.4.4
	cvxpy 1.2.1
	
	


cost calculations: Flexibility_Eta_v5_CostAnalysis.py
plots: Flexibility_Eta_v5_figures.py
