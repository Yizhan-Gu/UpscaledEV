clc;
clear all;
close all;

%%
addpath pvforecast/functions/

%% settings
lat = 32.69;
lon = -117.14;
loc2utc = 8/24; 
% Disable warning
warning('off','MATLAB:textio:io:UnableToGuessFormat');
%Constant optimization time horizon: 24 hrs.
ccolor.(char(65)) = [0.00 0.45 0.74];
ccolor.(char(66)) = [0.85 0.33 0.10];
ccolor.(char(67)) = [0.93 0.69 0.13];
ccolor.(char(68)) = [0.49 0.18 0.56];
ccolor.(char(69)) = [0.47 0.67 0.19];
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Workingdir = 'C:\Users\Anne\Desktop\SD Port\Cristian' ; % 'C:\Users\ccortesa\OneDrive - UC San Diego\SDport\Code';
Workingdir0 = Workingdir;
% 'C:\Users\ccortesa\OneDrive - UC San Diego\SDport\Code' 
% 'C:\Users\Anne\Desktop\SD Port'
% '/Users/avikghosh/Desktop/SD Port/Cristian Code'

% Load files
file1 = 'SDport_LOAD_v3.mat'; % Measured load
file2 = 'SAM_PV_NSRDB_2019_15min_v2.csv'; % Measured PV data
%file3 = 'PV_CS_KNN_DB.mat'; % Reforecaste input
file3 = 'PV_CS_KNN_DB_v2.mat'; % Reforecaste input
file4 = 'SAM_PV_HRRRt08z_2019_15min_v2.csv'; % 1 year of solar data
file5 = 'KNN_DB_3.mat'; % Load forecast input

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Cases (Difference objective functions)

% Choose the case!!!
% 'CaseF': Minimizing the cost (PDC+NCDC+EnergyCost+MoneyLossDueToBESSRoundTripEff)
% 'CaseG': Minimizing the interaction with the grid
Case = 'CaseF';

% Choose the way you want to implement the solution provided by the MPC
% 'a': battery setpoint is implemented at first
% 'b': grid import setpoint is implemented at first
ImpType = 'b'; 

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   
%% Versions (Different BESS SOC constraints)

% Choose the version!!!
% 'v3': SOC_forecast_15m(1,1)==SOC_opt_15m(step,1) & no constraint at the end
% 'v4': SOC_forecast_15m(1,1)==SOC_opt_15m(step,1) & SOC >= 50% at 24:00
% 'v5': SOC_forecast_15m(1,1)==SOC_opt_15m(step,1) & SOC >= 50% at endtime of each simulation horizon
% 'v6': v5 but with chance constraints implementeds

% 'v7': Case_v5 but tested with back substitution
% 'v8': Case_v7 but tested with back substitution

% 'v9': Case_v6 but eta = 0.7
% 'v10': Case_v6 but eta = 0.5

% 'v1': Case_v6 but var = 10
Version = 'v18d_UnderFcst'; 

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%     
%% Choose the time!!!
nyear = 2019;   
nmonth = 1;
days_ = eomday(nyear,nmonth);

% Timestep [x min/ 60 min] / MPC Rolling basis :
dt_m = 15; % min

% Timestep of the forecast files
dt_PVfcst = 15/60; % hours
dt_Ldfcst = 15/60; % hours
% Timestep of the measurement files
dt_PVmeas = 15/60; % hours
dt_Ldmeas = 15/60; % hours

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Other parameters
% Do plots at the end of each steps for each day
doplot = 1;
ShowFig = 'on'; % on or off
% Do plots for load forecast
doplot1 = 0;
% Do plots for solar forecast
doplot2 = 0;
% Do plots for Mean and Std
doplot3 = 0;

% Load forecast strategy
Load_frcst_model = 4;
% 1 - persistence forecasting (load at day D equal to load at day D-1) (Not ready)
% 2 - KNN forecasting ran once at 00z (Not ready)
% 3 - KNN forecasting updated at every step. This will update the load forecasting 
%     based on the latest data available
% 4 - Perfect Load Forecast
% 7 - Perfect Load Forecast + Gaussian White Noise

% PV forecast strategy
PV_frcst_model = 4;
% 1 - HRRR + SAM forecast
% 3 - HRRR + SAM forecast hourly
% 4 - Perfect PV power Forecast (NSRDB weather data)
% 5 - HRRR + SAM corrected every 15 min using latest PV data - forecast in "real time"
% 6 - HRRR + SAM corrected every 15 min using latest PV data + Weights
% 7 - Perfect PV power Forecast (NSRDB weather data) + Gaussian White Noise

% Parameters to apply reforecast (PV_frcst_model==5)
windows = [1,2,3,4]; % lagged averaged data in hours
PRCT = [5,10,20,30,70,80,90,95]; % percentiles for the probabilisti forecast

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Optimized battery scheduling for demand charge reduction using MPC

% SOC assigned in the constraint defined for the end of the day
ksoc_st1 = 0.5; %1.0; 

% demand rates % in reference to AL-TOU(<500kW) of sdg&e
Rate_NCD = 24.48; %20.62;          % demand charge rate non-coincident
Rate_PD = (19.14+19.23)/2;
Rate_Energy = 0.1; %0.00671;

% Penalty cycling coefficient
miu = 1e-6;

% MPC optimization parameters
str = "Infeasible";

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Timestep
dt_h = dt_m/60; % [h]
dt = dt_h; % [h]
sdt_m = sprintf('%02i',dt_m);

switch Load_frcst_model
    case 1
        sLoadfcst = 'Persistance Forecast (Not ready)';
    case 2
        sLoadfcst = 'KNN Forecast - Updated One per day (Not ready)';
    case 3
        sLoadfcst = 'KNN Forecast - Updated every step';
    case 4
        sLoadfcst = 'Perfect Forecast';
    case 7
        sLoadfcst = 'Perfect Forecast + Gaussian White Noise';        
end

switch PV_frcst_model
    case 1
        sPVfcst = 'HRRR updated daily';
    case 3
        sPVfcst = 'HRRR updated hourly';
    case 4
        sPVfcst = 'Perfect Forecast';
    case 5
        sPVfcst = 'HRRR updated hourly + Reforecasting';
    case 6
        sPVfcst = 'HRRR updated hourly + Reforecasting + Weights';    
    case 7
        sPVfcst = 'Perfect Forecast + Gaussian White Noise';         
end

% Chance Constraint
if strcmp(Version,'v6') % Version == 'v6'
    ChanceConst = 1;
elseif strcmp(Version,'v8') % Version == 'v8'
    ChanceConst = 1;
elseif strcmp(Version,'v9') % Version == 'v9'
    ChanceConst = 1;
elseif strcmp(Version,'v10') % Version == 'v10'
    ChanceConst = 1;
elseif strcmp(Version,'v1') % Version == 'v1'
    ChanceConst = 1;
else
    ChanceConst = 0;
end
NoChanceConst = abs(ChanceConst-1);

% Back Subsitution
if strcmp(Version,'v7') % Version == 'v7'
    BackSubstitution = 1;
elseif strcmp(Version,'v8') % Version == 'v8'
    BackSubstitution = 1;
else
    BackSubstitution = 0;
end
NoBackSubstitution = abs(BackSubstitution-1);

%% Step I: Input load data, PV generation data, batery specifications

freq = dt_m/60/24; % [days]

% reads load (kW) from the port of San Diego
tmp = load([Workingdir0,'\data\',file1]); 
Load_vals = tmp.LOAD;
Load_ts   = tmp.TS;
TimeSting_load = datetime(Load_ts,'ConvertFrom','datenum');

% Read PV generation measurements (reads modeled PV generation)
% PV generation is modeled using NREL's SAM.
% The model uses NSRDB weather data to simulate the PV generation.
% We use this data as the actual PV generation since we dont have yet real
% PV data
tmp = readtable([Workingdir0,'\data\',file2],'NumHeaderLines',1);
PV_meas_ts = datenum(tmp.Var1);
TimeSting_PV0 = datetime(PV_meas_ts,'ConvertFrom','datenum');
PV_meas_vals = tmp.Var2;

% It reads PV generation forecasted data.
if or(PV_frcst_model == 5,PV_frcst_model == 6)
    % loads KNN database with historical values
% %     load(['pvforecast/',file3]);
    load([Workingdir0,'\data\',file3]);
    
    % Remove nans
    Inan = ~any(isnan([PV_KNN_DB,PV_KNN_TAR]),2);
    PV_KNN_DB = PV_KNN_DB(Inan,:);
    PV_KNN_TAR = PV_KNN_TAR(Inan,:);
    PV_KNN_TS = PV_KNN_TS(Inan);
    
    % Keep original values
    PV_KNN_DBg = PV_KNN_DB;
    PV_KNN_TARg = PV_KNN_TAR;
    PV_KNN_TSg = PV_KNN_TS;
    
else
    tmp = readtable([Workingdir0,'\data\',file4],'NumHeaderLines',1);
    PV_fcst_ts0   = datenum(tmp.Var1);
    PV_fcst_vals0 = tmp.Var2;
    PV_fcst_ts_date0 = datetime(PV_fcst_ts0,'ConvertFrom','datenum');
end

% Battery specifications
BESS_pw = 700;                % Battery Power Vapacity (kW)
BESS_en = 2500;               % Battery Energy Capacity (kWh)
BESS_soc_init = 0.5;          % Battery initial state of charge
BESS_soc_min=0.2;
BESS_soc_max=0.8;

%% Step II: Run ONE month
simHorizon_StepNum = days_*24*60/dt_m;           % 24 hour time horizon used for simulation
PVfHorizon_StepNum = days_*24*60/(dt_PVfcst*60); % 24 hour time horizon used from PV forecast data
LdfHorizon_StepNum = days_*24*60/(dt_Ldfcst*60); % 24 hour time horizon used from Load forecast data

% Run ONE time for a month
syear = num2str(nyear);
smonth = sprintf('%02i',nmonth);

MMM = datestr(datetime(nyear,nmonth,1,0,0,0),'mmm');

CurrentTime = datetime('now','Format','yyyy-MM-dd hh:mm aa'); 
disp(CurrentTime)

disp([' Type of Solar Forecast: ',sPVfcst]) 
disp([' Type of Load Forecast: ',sLoadfcst])
disp([' Timestep (m): ',sdt_m])
disp([' Back Substitution?: ',num2str(BackSubstitution)])
disp([' Chance Constraints?: ',num2str(ChanceConst)])
disp([' Version: ',Version])

Is_cvx_working = true(simHorizon_StepNum,eomday(nyear,nmonth));
cvx_status_check=strings(simHorizon_StepNum,eomday(nyear,nmonth));

ndays = eomday(nyear,nmonth);

starting_day = 1; % Can change it to 1
end_date= 1; % ndays;

% % % Get Clear Sky PV generation for the month
% % % Select the data for the month
% % CS_ts = (datenum(nyear,nmonth,1-1):dt_m/60/24:datenum(nyear,nmonth+1,1)-dt_m/60/24+1)';
% % CS_PV_gen = CS_PV_generation(CS_ts + loc2utc,lat,lon,Workingdir0,freq);
% % TimeSting_CS_ts = datetime(CS_ts,'ConvertFrom','datenum');

fLoad = zeros(LdfHorizon_StepNum*ndays,LdfHorizon_StepNum);
tfLoad = zeros(LdfHorizon_StepNum*ndays,LdfHorizon_StepNum);
fPVgen = zeros(PVfHorizon_StepNum*ndays,PVfHorizon_StepNum);
tfPVgen = zeros(PVfHorizon_StepNum*ndays,PVfHorizon_StepNum);

aux_Ldmean = zeros(ndays,LdfHorizon_StepNum,LdfHorizon_StepNum);
aux_Ldstd = zeros(ndays,LdfHorizon_StepNum,LdfHorizon_StepNum);
aux_PVmean = zeros(ndays,PVfHorizon_StepNum,PVfHorizon_StepNum);
aux_PVstd = zeros(ndays,PVfHorizon_StepNum,PVfHorizon_StepNum);

aux_knn.Load = zeros(LdfHorizon_StepNum,29,LdfHorizon_StepNum);
aux_knn.PV = zeros(PVfHorizon_StepNum,30,PVfHorizon_StepNum);
aux_knn.PV_PCRT = zeros(PVfHorizon_StepNum,length(PRCT),PVfHorizon_StepNum);
aux_knn.ele = zeros(PVfHorizon_StepNum,PVfHorizon_StepNum);

param.Workingdir0 = Workingdir;
param.Workingdir1 = Workingdir; % [Workingdir,'\Operational'];
param.dt = dt;
param.dt_PVfcst = dt_PVfcst;
param.dt_Ldfcst = dt_Ldfcst;
param.dt_PVmeas = dt_PVmeas;
param.dt_m = dt_m;
param.windows = windows;
param.PRCT = PRCT;
param.PV_frcst_model = PV_frcst_model;
param.Load_frcst_model = Load_frcst_model;
% % param.SolarFv = SolarFv;
param.Version = Version;
param.lat = lat;
param.lon = lon;
param.loc2utc = loc2utc;
param.doplot = doplot;
param.doplot1 = doplot1;
param.doplot2 = doplot2;
param.doplot3 = doplot3;
param.file1 = file1;
param.file2 = file2;
param.file3 = file3;
param.file4 = file4;
param.file5 = file5;

MonMyImpltime = NaT(0,0);
MonMyImplBESS = [];
MonMyFcstBESS = [];
MonMyImplSOC = [];
MonMyFcstSOC = [];
MonMyImplGdImp = [];
MonMyFcstGdImp = [];
MonRealPVgen = [];
MonRealLoad = [];
MonFcstPVgen = [];
MonFcstLoad = [];
Moncvx_status_check = [];
MonTerminalCost = [];
MonTotalCost = [];

first_time = true;


th_NCD = 0;
th_PD = 0;

for nday = starting_day : end_date % eomday(nyear,nmonth)
 
    % Day to be simulated
    day_optm = datetime(datenum(nyear,nmonth,nday),'ConvertFrom','datenum');
    sday = sprintf('%02i',nday);
    % Sim timestep
    Sim_ts = [day_optm : minutes(dt_m) : day_optm+days(1)-minutes(1)]';  
    
    % Output folder name
    myname = [Case,ImpType,'_',Version,'_L',num2str(Load_frcst_model),...
        '_PV',num2str(PV_frcst_model),'_dt',sdt_m];

    Datafolder0 = ['/',myname];
    Datafolder2 = ['/',myname,'/',syear,smonth];
    Datafolder = ['/',myname,'/',syear,smonth,sday];

    if not(exist([Workingdir,'/Plots',Datafolder],'dir'))    
        mkdir([Workingdir,'/Plots',Datafolder]);
        if and(and(Load_frcst_model==7,PV_frcst_model==7),first_time)
            disp(' Have you copied the wgn Forecast?');
            pause;
            first_time = false;
        end
    end
    
    param.Datafolder = Datafolder;
    
    % Initialzing daily variables
    BESS_opt_15m        = zeros(simHorizon_StepNum,1);
    grid_import_opt_15m = zeros(simHorizon_StepNum,1);
    SOC_opt_15m         = zeros(simHorizon_StepNum+1,1);
    MyImpltime = NaT(0,0);
    MyImplBESS = [];
    MyFcstBESS = [];
    MyImplSOC = [];
    MyFcstSOC = [];
    MyImplGdImp = [];
    MyFcstGdImp = [];
    RealPVgen = [];
    RealLoad = [];
    FcstPVgen = [];
    FcstLoad = [];
    cvx_status_check = [];
    TerminalCost = [];
    TotalCost = [];    
    
    % Asigning initial SOC
    if nday == starting_day 
        SOC_opt_15m(1,1) = BESS_soc_init;
    else
        SOC_opt_15m(1,1) = last_SOC_opt_15m;
    end
        
% %     % CS PV generation
% %     % yesterday and today's CS PV
% %     Logic_meas0 = isbetween(TimeSting_CS_ts,day_optm-days(1),day_optm+days(1)-minutes(1));
% %     CS_PV3 = CS_PV_gen(Logic_meas0);
% %     CS_PV3_ts = TimeSting_CS_ts(Logic_meas0);
    
    % Measured PV generation
    % This Month PV
    %Logic_meas1 = isbetween(TimeSting_PV0,day_optm,day_optm+days(1)-minutes(1));
    Logic_meas1 = isbetween(TimeSting_PV0,day_optm,day_optm+days(days_)-minutes(1));
    meas_PV_ts = TimeSting_PV0(Logic_meas1);
    meas_PV = PV_meas_vals(Logic_meas1);

    % today and tomorrow's PV
    Logic_meas1 = isbetween(TimeSting_PV0,day_optm,day_optm+days(2)-minutes(1));
    meas_PV2_ts = meas_PV_ts; % TimeSting_PV0(Logic_meas1);
    meas_PV2 = meas_PV; %PV_meas_vals(Logic_meas1);

    % Interpolate PV measurements if simulation requires it
    if dt_h == dt_PVmeas
        aux_PV_meas = meas_PV;
    else
        disp('   PV_meas timestamp does not match simulation timestamp. Following simulation timestamp.')
        aux_ts = Sim_ts;
        aux_data2interp = meas_PV;
        aux_tsdata = meas_PV_ts;
        aux_PV_meas = interp1(aux_tsdata,aux_data2interp,aux_ts,'linear','extrap');
    end
    meas_PV0 = aux_PV_meas;
    
    % Knn PV generation forecast history of cases
    % Remove data
    if or(PV_frcst_model == 5,PV_frcst_model == 6)
        
    tmpf = datevec(PV_KNN_TSg);
% %     switch Version
% %         case 'vf7'
% %             % Remove same-day data
% %             II = tmpf(:,1)==nyear & tmpf(:,2)==nmonth & tmpf(:,3)==nday;
% %         case 'vf8'
            % Remove 1 week starting from current day
            aux_ds = datenum(datetime(nyear,nmonth,nday,0,0,0));
            aux_de = datenum(datetime(nyear,nmonth,nday+7,0,0,0));
            II = aux_ds <= PV_KNN_TSg & PV_KNN_TSg < aux_de;
% %         otherwise
% %             % Remove same-month data
% %             II = tmpf(:,1)==nyear & tmpf(:,2)==nmonth;
% %     end
    PV_KNN_DB = PV_KNN_DBg(~II,:);
    PV_KNN_TAR = PV_KNN_TARg(~II,:);
    PV_KNN_TS = PV_KNN_TSg(~II);
    % Calculate time difference with respect to previous midnight
    cyear = year(PV_KNN_TS);
    cmonth = month(PV_KNN_TS);
    cday = day(PV_KNN_TS);
    PV_KNN_rTS = PV_KNN_TS - datenum(cyear,cmonth,cday,zeros(size(cyear,1),1)...
        ,zeros(size(cyear,1),1),zeros(size(cyear,1),1));
    PV_KNN_DB1 = [PV_KNN_rTS,PV_KNN_DB];
    PV_KNN_TAR1 = PV_KNN_TAR;
    
    end
    
    % Measured Load for today and for today+tomorrow
    Logic_meas2 = isbetween(TimeSting_load,day_optm,day_optm+days(days_)-minutes(1));
    meas_load_power_ts = TimeSting_load(Logic_meas2);
    meas_load_power = Load_vals(Logic_meas2); % today's load
    Logic_meas2 = isbetween(TimeSting_load,day_optm,day_optm+days(days_)-minutes(1));
    meas_load_power2_ts = TimeSting_load(Logic_meas2);
    meas_load_power2 = Load_vals(Logic_meas2); % today and tomorrow's load
    TimeSting_today = TimeSting_load(Logic_meas2);    
    % load KNN "database" with 3 days together
    KNN=load(['data/',file5]); 

    % Interpolate Load measurements if simulation requires it
    if  dt_h == dt_Ldmeas
        aux_Load_meas = meas_load_power;
    else
        disp('   Load_meas timestamp does not match simulation timestamp. Following simulation timestamp.')
        aux_ts = Sim_ts;
        aux_data2interp = meas_load_power;
        aux_tsdata = meas_load_power_ts;
        aux_Load_meas = interp1(aux_tsdata,aux_data2interp,aux_ts,'linear','extrap');
    end
    meas_load_power = aux_Load_meas;
    
    % Run the day step by step
    for step = 1: 1 %simHorizon_StepNum
        step_ = sprintf('%02i',step);
        sstep = step;
        sstep_ = step_;  
        
        % Assign starting and endig time of the step
        start_time = datetime(nyear,nmonth,nday,floor((step-1)*dt),dt_m*rem((step-1),1/dt),0);   
        end_time = start_time +minutes(simHorizon_StepNum*dt_m);
        disp(['Start Time:',datestr(start_time,'mm dd, yyyy HH:MM:SS')])
        disp(['End Time:',datestr(end_time,'mm dd, yyyy HH:MM:SS')])      
        % Index vector for load forecast and measurements 
        step_ld = floor(sstep * dt / dt_Ldfcst);
        step_ld = max(step_ld,1);
        ii_Ld_ = (step_ld-1)+(1:1/dt_Ldfcst*24);
        % Index vector for PV measurements
        step_PV = floor(sstep*dt / dt_PVmeas);
        step_PV = max(step_PV,1);
        ii_PV_ = (step_PV-1)+(1:1/dt_PVmeas*24);        
        
        MPC_ts = (start_time:minutes(dt_m):end_time-minutes(dt_m))'; 
        
        %% Step III: Selects the forecast data (today and day before)        

        ccount = (nday-1)*simHorizon_StepNum + sstep;
        
        switch PV_frcst_model
            case 6                
                PVgenfcst_file = ['PVgenFcst_PV',num2str(PV_frcst_model),'_dt',sdt_m,'_',syear,smonth,sday,'.mat'];
                tmp_PVgenfcst = load([Workingdir0,'\data\PVgenFcst_Results\',syear,smonth,'\',PVgenfcst_file]);
                aux_PV_MPC = tmp_PVgenfcst.fPVgen_day(sstep,:)';
                aux_MPC_ts = tmp_PVgenfcst.tfPVgen_day(sstep,:)';
                aux_MPC_ts = datetime(aux_MPC_ts,'ConvertFrom','datenum');
                
                if sum(aux_MPC_ts==MPC_ts) == length(MPC_ts)
                    disp('   PV generation forecast is working well.')
                else
                    disp('   PV generation forecast is not working well.')
                end
        
            case 4
                aux_ts = NaT(length(MPC_ts),1);
                aux_PV = zeros(length(MPC_ts),1);
                for i = 1 :length(MPC_ts)
                    aux_ts(i) = meas_PV2_ts(meas_PV2_ts==MPC_ts(i));
                    aux_PV(i) = meas_PV2(meas_PV2_ts==MPC_ts(i));
                end
                aux_PV_MPC = aux_PV;
                aux_MPC_ts = aux_ts;
                
            case 7
                % Perfect Forecast with Noise
                output_wgnforecast = [Workingdir,'/Plots',Datafolder0,'/wgn_Fcst_L',num2str(Load_frcst_model),'_PV',num2str(PV_frcst_model),...
                    '_dt',sdt_m,'_',syear,smonth,sday,'.mat'];
                if exist(output_wgnforecast,'file') > 0
                    % Load the data
                    tmp = load(output_wgnforecast,'wgn_PV_fcst1','wgn_PV_fcst2');
                    aux_PV_MPC = tmp.wgn_PV_fcst1(:,step);
                    aux_PV_MPC2 = tmp.wgn_PV_fcst2(:,step);
                else
                    
                    % First day
                    aux_ts = NaT(length(MPC_ts),1);
                    aux_PV = zeros(length(MPC_ts),1);
                    for i = 1 :length(MPC_ts)
                        aux_ts(i) = meas_PV2_ts(meas_PV2_ts==MPC_ts(i));
                        aux_PV(i) = meas_PV2(meas_PV2_ts==MPC_ts(i));
                    end
                    % Add Gaussian White Noise to the Perfect Forecast
                    aux_day = aux_PV > 0;
                    aux_PV_MPC = aux_PV;
                    aux_PV_MPC(aux_day) = aux_PV(aux_day) + wgn(length(aux_PV(aux_day)),1,0).*std_wgn1;
                    aux_PV_MPC(aux_PV_MPC<0) = min(aux_PV);
                    aux_MPC_ts = aux_ts;
                    % Second day
                    aux_ts = NaT(length(MPC_ts2),1);
                    aux_PV = zeros(length(MPC_ts2),1);
                    for i = 1 :length(MPC_ts2)
                        aux_ts(i) = meas_PV2_ts(meas_PV2_ts==MPC_ts2(i));
                        aux_PV(i) = meas_PV2(meas_PV2_ts==MPC_ts2(i));
                    end
                    % Add Gaussian White Noise to the Perfect Forecast
                    aux_day = aux_PV > 0;
                    aux_PV_MPC2 = aux_PV;
                    aux_PV_MPC2(aux_day) = aux_PV(aux_day) + wgn(length(aux_PV(aux_day)),1,0).*std_wgn1;
                    aux_PV_MPC2(aux_PV_MPC2<0) = min(aux_PV);
                    
                    wgn_PV_fcst1 = cat(2,wgn_PV_fcst1,aux_PV_MPC);
                    wgn_PV_fcst2 = cat(2,wgn_PV_fcst2,aux_PV_MPC2);
                end      
        end        
        
        P_pv_mpc = aux_PV_MPC;         
        
        %% Load forecasting        
        % measured Load for today and yesterday
        % load data for the KNN forecast (Load(D-1))
        Logic_yesterday2 = isbetween(TimeSting_load,start_time-days(1),end_time-minutes(1)-days(1));
        hist_load_power = Load_vals(Logic_yesterday2); % previous' day load


        
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%        
        switch Load_frcst_model
            case 3
                % knn forecast
                loadfcst_file = ['LoadFcst_L',num2str(Load_frcst_model),'_dt',sdt_m,'_',syear,smonth,sday,'.mat'];
                tmp_loadfcst = load([Workingdir0,'\data\LoadFcst_Results\',syear,smonth,'\',loadfcst_file]);
                aux_Load_MPC = tmp_loadfcst.fLoad_day(sstep,:)';
                aux_MPC_ts = tmp_loadfcst.tfLoad_day(sstep,:)';
                aux_MPC_ts = datetime(aux_MPC_ts,'ConvertFrom','datenum');
                
                if sum(aux_MPC_ts==MPC_ts) == length(MPC_ts)
                    disp('   Load forecast is working well.')
                else
                    disp('   Load forecast is not working well.')
                end
            case 4
                % Perfect Forecast
                aux_ts = NaT(length(MPC_ts),1);
                aux_load = zeros(length(MPC_ts),1);
                for i = 1 :length(MPC_ts)
                    aux_ts(i) = meas_load_power2_ts(meas_load_power2_ts==MPC_ts(i));
                    aux_load(i) = meas_load_power2(meas_load_power2_ts==MPC_ts(i));
                end
                aux_Load_MPC = aux_load;
                aux_MPC_ts = aux_ts;
            case 7
                % Perfect Forecast with Noise
                output_wgnforecast = [Workingdir,'/Plots',Datafolder0,'/wgn_Fcst_L',num2str(Load_frcst_model),'_PV',num2str(PV_frcst_model),...
                    '_dt',sdt_m,'_',syear,smonth,sday,'.mat'];
                if exist(output_wgnforecast,'file') > 0
                    % Load the data
                    tmp = load(output_wgnforecast,'wgn_Load_fcst1','wgn_Load_fcst2');
                    aux_Load_MPC = tmp.wgn_Load_fcst1(:,step);
                    aux_Load_MPC2 = tmp.wgn_Load_fcst2(:,step);
                else
                    % First day
                    aux_ts = NaT(length(MPC_ts),1);
                    aux_load = zeros(length(MPC_ts),1);
                    for i = 1 :length(MPC_ts)
                        aux_ts(i) = meas_load_power2_ts(meas_load_power2_ts==MPC_ts(i));
                        aux_load(i) = meas_load_power2(meas_load_power2_ts==MPC_ts(i));
                    end
                    aux_Load_MPC = aux_load + wgn(length(MPC_ts),1,0).*std_wgn2;
                    aux_MPC_ts = aux_ts;
                    % Second day
                    aux_ts = NaT(length(MPC_ts2),1);
                    aux_load = zeros(length(MPC_ts2),1);
                    for i = 1 :length(MPC_ts2)
                        aux_ts(i) = meas_load_power2_ts(meas_load_power2_ts==MPC_ts2(i));
                        aux_load(i) = meas_load_power2(meas_load_power2_ts==MPC_ts2(i));
                    end
                    aux_Load_MPC2 = aux_load + wgn(length(MPC_ts),1,0).*std_wgn2;
                    
                    wgn_Load_fcst1 = cat(2,wgn_Load_fcst1,aux_Load_MPC);
                    wgn_Load_fcst2 = cat(2,wgn_Load_fcst2,aux_Load_MPC2);
                end                
                
        end        
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%        
        % Load forecasting for the [step,step+96]
        MPC_horizon_load = aux_Load_MPC;
        
        %% Logic for SOC >= 50% at timepoint 24:00
        Time2400 = 98-step;
        
        %% Logic for start and end timepoint of Peak Period (PP)


        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        %%
        c1 = Rate_NCD;
        c2 = Rate_PD;
        c3 = Rate_Energy*dt;
        c4 = (1-0.8)*0.5*dt*Rate_Energy;
        T = simHorizon_StepNum;
        p = BESS_pw;
        e = BESS_en;
        MonthlyTime = (start_time:minutes(dt_m):end_time-minutes(dt_m))';
        logic_PP = (hour(MonthlyTime) >= 16) + (hour(MonthlyTime) < 21) == 2; 



        %% Optimize with forecast/receding time horizon of 24 hrs and time step of 15 mins
        cvx_begin quiet
        variable  U1(T,1); 
        variable  obj;
        variables  BESS_forecast_15m(T,1) SOC_forecast_15m(T+1,1)  
                
        subject to
         
        minimize(obj)

%         obj >= c1*max(max(U1),th_NCD)+...
%             +Logic_PP1*c2*max(max(U1(ind_PP1_Start:ind_PP1_End)),th_PD)...
%             +Logic_PP2*c2*max(max( [max(0,U1(ind_PP1_Start:ind_PP1_End)); max(0,U1(ind_PP2_Start:ind_PP2_End))] ),th_PD)...
%             +Logic_PP3*c2*max(max(U1(ind_PP2_Start:ind_PP2_End)),th_PD)...
%             +c3*ones(1,T)*U1...
%             +c4*ones(1,T)*abs(BESS_forecast_15m)*p;

        obj >= c1*max(max(U1),th_NCD)+...
            +c2*max(max(U1(logic_PP)),th_PD)...
            +c3*ones(1,T)*U1...
            +c4*ones(1,T)*abs(BESS_forecast_15m)*p;        
                               
        SOC_forecast_15m(:,1)   >= BESS_soc_min;
        SOC_forecast_15m(:,1)   <= BESS_soc_max;
        SOC_forecast_15m(1,1)   == SOC_opt_15m(step,1);
        SOC_forecast_15m(end)   >= ksoc_st1;
        for i = 1:T
            SOC_forecast_15m(i+1) == SOC_forecast_15m(i) - BESS_forecast_15m(i)*dt*p/e;
        end
        BESS_forecast_15m >= -1;
        BESS_forecast_15m <= 1;
        U1 + p*BESS_forecast_15m + P_pv_mpc == MPC_horizon_load;  
                
        cvx_end

        

% %         cvx_status_check(step,nday)=cvx_status;
        cvx_status_check = cat(1,cvx_status_check,cellstr(cvx_status));
        TerminalCost = cat(1,TerminalCost,0);
        aux_TotalCost = c1*max(U1)+...
                    +c2*max(max(U1),0)...
                    +c3*ones(1,T)*U1...
                    +c4*ones(1,T)*abs(BESS_forecast_15m)*p;
        TotalCost = cat(1,TotalCost,aux_TotalCost);        
        
        grid_import_forecast_15m = U1;
        
        SOC_opt_15m(step+1,1) = SOC_forecast_15m(2);
        grid_import_opt_15m(step,1) = grid_import_forecast_15m(1);

        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        % Implement MPC results considering measurement data
        if strcmp(ImpType,'b')
            % Implement grid import setpoint first (Roy et al., 2021)
            if contains(cvx_status, str)
                % If MPC does not work, controller will satisfy the demand and then
                % it will storage the remaining power.
                % 1st. Satisfy the load with PV power
                % 2nd. Utilize battery (battery is discharged if PV power is not enough)
                % 3rd. Export or import power from the grid 
                % Checking if PV power satisfied the load            
                 
                 BESS_forecast_15m(1,1) = (meas_load_power(step,1) - meas_PV0(step,1))/BESS_pw; 
                 BESS_opt_15m(step,1) = BESS_forecast_15m(1,1);
                 BESS_output_opt_aux = BESS_opt_15m(step,1) * BESS_pw;
                 SOC_opt_15m(step+1,1) = SOC_opt_15m(step,1)-dt*BESS_output_opt_aux/BESS_en;
               
                 if (SOC_opt_15m(step+1,1) > BESS_soc_max)
                  
                    SOC_opt_15m(step+1,1) = BESS_soc_max;
                    BESS_output_opt_aux = (SOC_opt_15m(step+1,1)-SOC_opt_15m(step,1)) * BESS_en / dt;
                    BESS_opt_15m(step,1)= BESS_output_opt_aux/BESS_pw;
                 end
                 
                  if (SOC_opt_15m(step+1,1) < BESS_soc_min)
                    SOC_opt_15m(step+1,1) = BESS_soc_min;
                    BESS_output_opt_aux = (SOC_opt_15m(step+1,1)-SOC_opt_15m(step,1)) * BESS_en / dt;
                    BESS_opt_15m(step,1)= BESS_output_opt_aux/BESS_pw;
                  end
                                 
                grid_import_opt_15m(step,1) = meas_load_power(step,1) - meas_PV0(step,1) - BESS_output_opt_aux;
                               
                Is_cvx_working(step,nday) = false;
                                
            else
                % If MPC works, assigns values to the storage system
                % 1st. Keep grid import setpoint
                % 2nd. Assign battery setpoint accordingly
                
                % Check if it is enough power from PV and after demand is satisfied
                grid_import_opt_15m(step,1) = grid_import_forecast_15m(1,1);
                BESS_output_opt_aux = meas_load_power(step,1) - meas_PV0(step,1) - grid_import_opt_15m(step,1);
                SOC_opt_15m(step+1,1) = SOC_opt_15m(step,1) - dt * BESS_output_opt_aux / BESS_en;
                
                % Check if the battery setpoint surpasses SOC limits
                if SOC_opt_15m(step+1,1) < BESS_soc_min
                    % Assign SOC min limit to the next SOC
                    SOC_opt_15m(step+1,1) = BESS_soc_min;
                    % Update the battery setpoint
                    BESS_output_opt_aux = -(SOC_opt_15m(step+1,1)-SOC_opt_15m(step,1)) * BESS_en / dt;
                    % Update grid import setpoint
                    grid_import_opt_15m(step,1) = meas_load_power(step,1) - meas_PV0(step,1) - BESS_output_opt_aux;
                    
                elseif SOC_opt_15m(step+1,1) > BESS_soc_max
                    % Assign SOC mmax limit to the next SOC
                    SOC_opt_15m(step+1,1) = BESS_soc_max;
                    % Update the battery setpoint
                    BESS_output_opt_aux = -(SOC_opt_15m(step+1,1)-SOC_opt_15m(step,1)) * BESS_en / dt;
                    % Update grid import setpoint
                    grid_import_opt_15m(step,1) = meas_load_power(step,1) - meas_PV0(step,1) - BESS_output_opt_aux;                    
                end
                
                BESS_opt_15m(step,1) = BESS_output_opt_aux / BESS_pw;               
            end

        else
            % Implement battery setpoint first
       
         end
        
        last_SOC_opt_15m = SOC_opt_15m(step+1,1);
        test = grid_import_opt_15m(step,1);
        th_NCD = max(th_NCD,test(1));
        if (step >= 65) && (step <= 84) 
            th_PD  = max(th_PD, test(1));
        end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        %% Save Monthly Data
        if step == 1
            MyImplSOC = SOC_opt_15m(step,1);
            MyFcstSOC = SOC_forecast_15m(step,1);
        end
        MyImpltime = cat(1,MyImpltime,start_time);
        MyImplBESS = cat(1,MyImplBESS,BESS_output_opt_aux);
        MyFcstBESS = cat(1,MyFcstBESS,BESS_forecast_15m(1,1)*BESS_pw);
        MyImplSOC = cat(1,MyImplSOC,SOC_opt_15m(step+1,1));
        MyFcstSOC = cat(1,MyFcstSOC,SOC_forecast_15m(2,1));
        MyImplGdImp = cat(1,MyImplGdImp,grid_import_opt_15m(step,1));
        MyFcstGdImp = cat(1,MyFcstGdImp,grid_import_forecast_15m(1,1));
        RealPVgen = cat(1,RealPVgen,meas_PV0(step,1));
        RealLoad = cat(1,RealLoad,meas_load_power(step,1)); 
        FcstPVgen = cat(1,FcstPVgen,P_pv_mpc(1,1));
        FcstLoad = cat(1,FcstLoad,MPC_horizon_load(1,1));

        % Plot results when optimization is implemented
        if doplot
%             f2 = figure('visible',ShowFig); hold on
%             figtime = MyImpltime;
%             h1 = stairs(figtime,RealLoad - RealPVgen,'LineWidth',2,'Color',ccolor.(char(65)));
%             h2 = stairs(figtime,MyImplBESS,'LineWidth',2,'Color',ccolor.(char(67)));
%             h3 = stairs(figtime,MyFcstBESS,':','LineWidth',2,'Color',ccolor.(char(67)));
%             h4 = stairs(figtime,MyImplGdImp,'LineWidth',2,'Color',ccolor.(char(68)));
%             ylabel('[kW]'); ylim([-600 600])
%             yyaxis right;
%             h5 = plot([figtime; figtime(end)+minutes(dt_m)],MyImplSOC,'LineWidth',2,'Color',ccolor.(char(69)));
%             set(gca,'Fontsize',14)
%             xlim([datetime(nyear,nmonth,nday,0,0,0) datetime(nyear,nmonth,nday+1,0,0,0)])
%             ylabel('SOC [-]'); ylim([0 1])
%             L = legend([h1,h2,h3,h4,h5],'Real Net Load','Opt BESS','Fct BESS','Opt GdImp','Opt SOC');
%             L.Location = 'southeast';
%             L.FontSize = 8;
%             saveas(f2,[Workingdir,'/Plots',Datafolder,'/RealData_step',step_],'png');
%             saveas(f2,[Workingdir,'/Plots',Datafolder,'/RealData_step',step_],'fig');
        end         
        
        
        % Plot MPC data
        if doplot
            figure(100);
            subplot(3,1,1) ; hold on
            figtime = (start_time:minutes(dt_m):end_time);
            h1 = stairs(figtime,[MPC_horizon_load;MPC_horizon_load(end)],'LineWidth',2,'Color',ccolor.(char(65)));
            h2 = stairs([meas_load_power2_ts;meas_load_power2_ts(end)],[meas_load_power2;meas_load_power2(end)],':','LineWidth',1,'Color',ccolor.(char(65)));
            h3 = stairs(figtime,[P_pv_mpc;P_pv_mpc(end)],'LineWidth',2,'Color',ccolor.(char(66)));
            h4 = stairs([meas_PV2_ts;meas_PV2_ts(end)],[meas_PV2;meas_PV2(end)],':','LineWidth',1,'Color',ccolor.(char(66)));
            h5 = stairs(figtime,[BESS_pw*BESS_forecast_15m;BESS_pw*BESS_forecast_15m(end)],'LineWidth',2,'Color',ccolor.(char(67)));
            h6 = stairs(figtime,[grid_import_forecast_15m;grid_import_forecast_15m(end)],'LineWidth',2,'Color',ccolor.(char(68)));
            ylabel('[kW]'); ylim([-600 600])
            yyaxis right;
            set(gca,'ycolor',ccolor.(char(69)))
            h7 = plot(figtime,SOC_forecast_15m,'LineWidth',2,'Color',ccolor.(char(69))); hold off
            xlim([datetime(nyear,nmonth,nday,0,0,0) datetime(nyear,nmonth,nday+10,0,0,0)])
            ylabel('SOC [-]'); ylim([0 1])
            set(gca,'Fontsize',14)
            L = legend([h1,h2,h3,h4,h5,h6,h7],'MPC Load','Real Load','MPC PV','Real PV','MPC BESS','MPC GridIm','MPC SOC');
            L.Location = 'southeast';
            L.FontSize = 8;

            subplot(3,1,2) ; hold on
            h1 = stairs(figtime,[MPC_horizon_load;MPC_horizon_load(end)],'LineWidth',2,'Color',ccolor.(char(65)));
            h2 = stairs([meas_load_power2_ts;meas_load_power2_ts(end)],[meas_load_power2;meas_load_power2(end)],':','LineWidth',1,'Color',ccolor.(char(65)));
            h3 = stairs(figtime,[P_pv_mpc;P_pv_mpc(end)],'LineWidth',2,'Color',ccolor.(char(66)));
            h4 = stairs([meas_PV2_ts;meas_PV2_ts(end)],[meas_PV2;meas_PV2(end)],':','LineWidth',1,'Color',ccolor.(char(66)));
            h5 = stairs(figtime,[BESS_pw*BESS_forecast_15m;BESS_pw*BESS_forecast_15m(end)],'LineWidth',2,'Color',ccolor.(char(67)));
            h6 = stairs(figtime,[grid_import_forecast_15m;grid_import_forecast_15m(end)],'LineWidth',2,'Color',ccolor.(char(68)));
            ylabel('[kW]'); ylim([-600 600])
            yyaxis right;
            set(gca,'ycolor',ccolor.(char(69)))
            h7 = plot(figtime,SOC_forecast_15m,'LineWidth',2,'Color',ccolor.(char(69))); hold off
            xlim([datetime(nyear,nmonth,nday+10,0,0,0) datetime(nyear,nmonth,nday+20,0,0,0)])
            ylabel('SOC [-]'); ylim([0 1])
            set(gca,'Fontsize',14)

            subplot(3,1,3) ; hold on
            figtime = (start_time:minutes(dt_m):end_time);
            h1 = stairs(figtime,[MPC_horizon_load;MPC_horizon_load(end)],'LineWidth',2,'Color',ccolor.(char(65)));
            h2 = stairs([meas_load_power2_ts;meas_load_power2_ts(end)],[meas_load_power2;meas_load_power2(end)],':','LineWidth',1,'Color',ccolor.(char(65)));
            h3 = stairs(figtime,[P_pv_mpc;P_pv_mpc(end)],'LineWidth',2,'Color',ccolor.(char(66)));
            h4 = stairs([meas_PV2_ts;meas_PV2_ts(end)],[meas_PV2;meas_PV2(end)],':','LineWidth',1,'Color',ccolor.(char(66)));
            h5 = stairs(figtime,[BESS_pw*BESS_forecast_15m;BESS_pw*BESS_forecast_15m(end)],'LineWidth',2,'Color',ccolor.(char(67)));
            h6 = stairs(figtime,[grid_import_forecast_15m;grid_import_forecast_15m(end)],'LineWidth',2,'Color',ccolor.(char(68)));
            ylabel('[kW]'); ylim([-600 600])
            yyaxis right;
            set(gca,'ycolor',ccolor.(char(69)))
            h7 = plot(figtime,SOC_forecast_15m,'LineWidth',2,'Color',ccolor.(char(69))); hold off
            xlim([datetime(nyear,nmonth,nday+20,0,0,0) datetime(nyear,nmonth+1,1,0,0,0)])
            ylabel('SOC [-]'); ylim([0 1])
            set(gca,'Fontsize',14)
            %saveas(f1,[Workingdir,'/Plots',Datafolder,'/MPCData_step',step_],'png');
            %saveas(f1,[Workingdir,'/Plots',Datafolder,'/MPCDataz_step',step_],'fig');
            saveas(gcf,[Workingdir,'/Plots',Datafolder2,'/Monthly_MPCData_PerfectMonth'],'png');
            saveas(gcf,[Workingdir,'/Plots',Datafolder2,'/Monthly_MPCData_PerfectMonth'],'fig');
        end

% % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% % %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        %close all;


        
    end % End of the step

%     MonMyImpltime = cat(1,MonMyImpltime,MyImpltime);
%     MonMyImplBESS = cat(1,MonMyImplBESS,MyImplBESS);
%     MonMyFcstBESS = cat(1,MonMyFcstBESS,MyFcstBESS);
%     if nday < end_date
%         MonMyImplSOC = cat(1,MonMyImplSOC,MyImplSOC(1:end-1));
%         MonMyFcstSOC = cat(1,MonMyFcstSOC,MyFcstSOC(1:end-1));
%     else
%         MonMyImplSOC = cat(1,MonMyImplSOC,MyImplSOC);
%         MonMyFcstSOC = cat(1,MonMyFcstSOC,MyFcstSOC);
%     end
%     MonMyImplGdImp = cat(1,MonMyImplGdImp,MyImplGdImp);
%     MonMyFcstGdImp = cat(1,MonMyFcstGdImp,MyImplGdImp);
%     MonRealPVgen = cat(1,MonRealPVgen,RealPVgen);
%     MonRealLoad = cat(1,MonRealLoad,RealLoad);
%     MonFcstPVgen = cat(1,MonFcstPVgen,FcstPVgen);
%     MonFcstLoad = cat(1,MonFcstLoad,FcstLoad);
% 
% outputdata = [Workingdir,'/Plots',Datafolder,'/MPCResults',Case,ImpType,'_',Version,'_',syear,smonth,sday,'_PV',...
%     num2str(PV_frcst_model),'_Ld',num2str(Load_frcst_model),'_dt',sdt_m,'.mat'];
% 
% % Pending
% MyTable = table(MyImpltime,RealLoad,RealPVgen,MyImplBESS,MyImplGdImp,MyImplSOC(1:end-1), ...
%     TotalCost,TerminalCost,FcstLoad,FcstPVgen,MyFcstBESS,MyFcstGdImp,MyFcstSOC(1:end-1), ...
%     cvx_status_check);
% 
% save(outputdata,'MyTable');
% 
% % Save WGN forecast
% output_wgnforecast = [Workingdir,'/Plots',Datafolder0,'/wgn_Fcst_L',num2str(Load_frcst_model),'_PV',num2str(PV_frcst_model),...
%     '_dt',sdt_m,'_',syear,smonth,sday,'.mat'];
% if and(exist(output_wgnforecast,'file') == 0,PV_frcst_model == 7)
%     save(output_wgnforecast,'wgn_PV_fcst1','wgn_PV_fcst2','wgn_Load_fcst1','wgn_Load_fcst2');
% end
% 
 end % End of the day
% 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   
% 
% %% Monthly Plot
% % Monthly Table
% Monthly_Table = table([MonMyImpltime; MonMyImpltime(end)+minutes(dt_m)],...     %time
%     [MonFcstLoad; MonFcstLoad(end)],...             %load_f
%     [MonRealLoad; MonRealLoad(end)],...             %load_r
%     [MonFcstPVgen; MonFcstPVgen(end)],...            %pv_f
%     [MonRealPVgen; MonRealPVgen(end)],...            %pv_r
%     [MonMyFcstBESS; MonMyFcstBESS(end)],...           %BESS dispatch forecasted    
%     [MonMyImplBESS; MonMyImplBESS(end)],...           %BESS dispatch 
%     [MonMyFcstGdImp; MonMyFcstGdImp(end)],...          %grid_f
%     [MonMyImplGdImp; MonMyImplGdImp(end)],...          %grid_r
%     MonMyFcstSOC,...   %BESS SOC_f
%     MonMyImplSOC);     %BESS SOC_r
% 
% C1 = {'Time [-]',...
%     'fc Load [kW]',...
%     'rl Load [kW]',...
%     'fc PV [kW]',...
%     'rl PV [kW]',...
%     'fc BESS [kW]',...    
%     'rl BESS [kW]',...
%     'fc Grid Import [kW]',...
%     'rl Grid Import [kW]',...
%     'fc SOC [kW]',...
%     'rl SOC [kW]'};
% 
% Monthly_Table.Properties.VariableNames=C1;
% tablename = [Case,ImpType,'_',Version,'_L',num2str(Load_frcst_model),...
%     '_PV',num2str(PV_frcst_model),'_dt',sdt_m,'_Monthly_Table_',MMM,'.mat'];
% save([Workingdir,'\Results\',tablename],'Monthly_Table');
% 
% % Reading the data
% Series_Time = [MonMyImpltime; MonMyImpltime(end)+minutes(dt_m)];
% Series_Load = MonRealLoad;
% Series_PV = MonRealPVgen;
% Series_BESS = MonMyImplBESS;
% Series_GridImp = MonMyImplGdImp;
% Series_SOC = MonMyImplSOC; % it has one extra data
% logic_ThisMonth = (Series_Time >= datetime(nyear,nmonth,1,0,0,0)) + (Series_Time < datetime(nyear,nmonth+1,1,0,0,0)) == 2;
% logic_ThisMonth1 = (Series_Time >= datetime(nyear,nmonth,1,0,0,0)) + (Series_Time <= datetime(nyear,nmonth+1,1,0,0,0)) == 2;
% MonthlyTime = Series_Time(logic_ThisMonth);
% MonthlyTime1 = Series_Time(logic_ThisMonth1);
% MonthlyLoad = Series_Load(logic_ThisMonth);
% MonthlyPV = Series_PV(logic_ThisMonth);
% MonthlyBESS = Series_BESS(logic_ThisMonth);
% MonthlyGridImp = Series_GridImp(logic_ThisMonth);
% MonthlySOC = Series_SOC(logic_ThisMonth1);
% MonthlyTime_ = MonthlyTime1;
% MonthlyLoad_ = [MonthlyLoad;MonthlyLoad(end)];
% MonthlyPV_ = [MonthlyPV;MonthlyPV(end)];
% MonthlyBESS_ = [MonthlyBESS;MonthlyBESS(end)];
% MonthlyGridImp_ = [MonthlyGridImp;MonthlyGridImp(end)];
% MonthlySOC_ = MonthlySOC;
% 
% 
% figure(32);
% Subplot_1_i = 1;
% Subplot_1_f = sum(MonthlyTime_ <= datetime(nyear,nmonth,11,0,0,0)); %plot 1th-10th
% Subplot_2_i = Subplot_1_f;
% Subplot_2_f = sum(MonthlyTime_ <= datetime(nyear,nmonth,21,0,0,0)); %plot 10th-20th
% Subplot_3_i = Subplot_2_f;
% 
% % Plotting the data
% subplot(3,1,1)
% hold on
% h1 = stairs(MonthlyTime_(Subplot_1_i:Subplot_1_f),MonthlyLoad_(Subplot_1_i   :Subplot_1_f),'LineWidth',1.5,'Color',ccolor.(char(65)));
% h2 = stairs(MonthlyTime_(Subplot_1_i:Subplot_1_f),MonthlyPV_(Subplot_1_i     :Subplot_1_f),'LineWidth',1.5,'Color',ccolor.(char(66)));
% h3 = stairs(MonthlyTime_(Subplot_1_i:Subplot_1_f),MonthlyBESS_(Subplot_1_i   :Subplot_1_f),'LineWidth',1.5,'Color',ccolor.(char(67)));
% h4 = stairs(MonthlyTime_(Subplot_1_i:Subplot_1_f),MonthlyGridImp_(Subplot_1_i:Subplot_1_f),'LineWidth',3,'Color',ccolor.(char(68)));
% ylabel('[kW]')
% ylim([-600 600])
% yyaxis right;
% ylabel('SOC [-]')
% h6 = plot(MonthlyTime_(Subplot_1_i:Subplot_1_f),MonthlySOC_(Subplot_1_i:Subplot_1_f),'LineWidth',3,'Color',ccolor.(char(69)));
% xlim([MonthlyTime_(Subplot_1_i) MonthlyTime_(Subplot_1_f)])
% ylim([0 1])
% set(gca,'Fontsize',14)
% legend([h1,h2,h3,h4,h6],'Real Load','Real PV','Impd BESS','Impd GridIm','Impd SOC')
% legend('Location','southeast')
% subplot(3,1,2)
% hold on
% h1 = stairs(MonthlyTime_(Subplot_2_i:Subplot_2_f),MonthlyLoad_(Subplot_2_i:Subplot_2_f),'LineWidth',1.5,'Color',ccolor.(char(65)));
% h2 = stairs(MonthlyTime_(Subplot_2_i:Subplot_2_f),MonthlyPV_(Subplot_2_i:Subplot_2_f),'LineWidth',1.5,'Color',ccolor.(char(66)));
% h3 = stairs(MonthlyTime_(Subplot_2_i:Subplot_2_f),MonthlyBESS_(Subplot_2_i:Subplot_2_f),'LineWidth',1.5,'Color',ccolor.(char(67)));
% h4 = stairs(MonthlyTime_(Subplot_2_i:Subplot_2_f),MonthlyGridImp_(Subplot_2_i:Subplot_2_f),'LineWidth',3,'Color',ccolor.(char(68)));
% ylabel('[kW]')
% ylim([-600 600])
% yyaxis right;
% ylabel('SOC [-]')
% h6 = plot(MonthlyTime_(Subplot_2_i:Subplot_2_f),MonthlySOC_(Subplot_2_i:Subplot_2_f),'LineWidth',3,'Color',ccolor.(char(69)));
% xlim([MonthlyTime_(Subplot_2_i) MonthlyTime_(Subplot_2_f)])
% ylim([0 1])
% set(gca,'Fontsize',14)
% subplot(3,1,3)
% hold on
% h1 = stairs(MonthlyTime_(Subplot_3_i:end),MonthlyLoad_(Subplot_3_i:end),'LineWidth',1.5,'Color',ccolor.(char(65)));
% h2 = stairs(MonthlyTime_(Subplot_3_i:end),MonthlyPV_(Subplot_3_i:end),'LineWidth',1.5,'Color',ccolor.(char(66)));
% h3 = stairs(MonthlyTime_(Subplot_3_i:end),MonthlyBESS_(Subplot_3_i:end),'LineWidth',1.5,'Color',ccolor.(char(67)));
% h4 = stairs(MonthlyTime_(Subplot_3_i:end),MonthlyGridImp_(Subplot_3_i:end),'LineWidth',3,'Color',ccolor.(char(68)));
% ylabel('[kW]')
% ylim([-600 600])
% yyaxis right;
% ylabel('SOC [-]')
% h6 = plot(MonthlyTime_(Subplot_3_i:end),MonthlySOC_(Subplot_3_i:end),'LineWidth',3,'Color',ccolor.(char(69)));
% xlim([MonthlyTime_(Subplot_3_i) MonthlyTime_(end)])
% ylim([0 1])
% set(gca,'Fontsize',14)
% 
% Datafolder2 = ['/',Case,ImpType,'_',Version,'_L',num2str(Load_frcst_model),'_PV',num2str(PV_frcst_model),'_dt',sdt_m,'/',syear,smonth];
% if not(exist([Workingdir,'/Plots',Datafolder2],'dir'))
%     mkdir([Workingdir,'/Plots',Datafolder2]);
% end
% saveas(gcf,[Workingdir,'/Plots',Datafolder2,'/Monthly_MPCData'],'png');
% saveas(gcf,[Workingdir,'/Plots',Datafolder2,'/Monthly_MPCData'],'fig');
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%    
% 
%% Calculating Additional Metrics
NCD = max(grid_import_forecast_15m);
NCDC = Rate_NCD*NCD;

PD = max(grid_import_forecast_15m(logic_PP));
PDC = Rate_PD*PD;

Loss_BESS = Rate_Energy*0.2*dt*sum(abs(p*BESS_forecast_15m))/2;
EnergyPrice = Rate_Energy*dt*sum(grid_import_forecast_15m);
Cost = NCDC+PDC+Loss_BESS+EnergyPrice;

BESSAvgDailyCycleNum = sum(abs(p*BESS_forecast_15m)*dt)/(2*BESS_en)/eomday(nyear,nmonth);
BESSAvgSOC = sum(SOC_forecast_15m)/length(SOC_forecast_15m);


% 
% Results_Table = table(cellstr([syear,smonth]),NCDC,PDC,Loss_BESS,EnergyPrice,...
%     Cost,BESSAvgDailyCycleNum,BESSAvgSOC,AvgDailyNCD,AvgDailyPD,...
%     'VariableNames',{'Time [-]','NCDC [$]','PDC [$]','Loss_BESS [$]',...
%     'EnergyPrice [$]','Cost [$]','BESS avg daily cycle num [-]',...
%     'BESS avg SOC [-]','avg daily NCD [kW]','avg daily PD [kW]'});
% 
% tablenameR = [Case,ImpType,'_',Version,'_L',num2str(Load_frcst_model),...
%     '_PV',num2str(PV_frcst_model),'_dt',sdt_m,'_MonthlyRevenue_',MMM,'.mat'];
% save([Workingdir,'\Results\',tablenameR],'Results_Table');


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%    
CurrentTime = datetime('now','Format','yyyy-MM-dd hh:mm aa'); 
disp(CurrentTime)
