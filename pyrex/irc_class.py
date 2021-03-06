"""
Class for calculating IRC using Morokuma Algorithm
"""

import sys
import os
import psi4
import json
import numpy as np



def JSON2XYZ(input_params):
    charge = input_params['molecule']['molecular_charge']
    mult = input_params['molecule']['molecular_multiplicity']
    geom = ''
    geom += '\n%d %d\n' %(charge, mult)
    symbols = input_params['molecule']['symbols']
    geometry = input_params['molecule']['geometry']
    for i in range(len(symbols)):
        geom += "%s  " %symbols[i]
        for j in range(3):
            if(j==2):
                geom += "   %f   \n" %geometry[(i + 2*i) + j]
            else:
                geom += "   %f   " %geometry[(i + 2*i) + j]
    #print(geom)
    return geom
    
class ToolKit():
    # Placeholder for Common Data
    def __init__(self,name):
        self.natoms=0
        self.basis = '3-21G'
        self.method = 'SCF'
        self.level_of_theory = "%s/%s" %(self.method,self.basis)
        self.alpha=0.1
        self.basename='.'.join(name.split('.')[:-1])
        self.out=open("%s.log"%(self.basename),'a',1)
        self.delta=0.05
        self.direction=1
        self.energies=[]
        self.energy=0.00
        self.geos=[]
        self.restart=False
        self.geometry=[]
        self.guessfn=''
        self.damp=0.05
        self.algorithm=1
        self.autodamp=False
        self.prevgrad=0.0
        self.hessfn=''
        self.maxdispl=0.01
        self.mode=4
        self.dgrad=0.0
        self.npoints=25
        self.template=[]
        self.keywords={}
        self.tolerance=1.0e-04
        self.orcacmd='UNDEFINED'
        self.ReadInput(name)
        self.ComputeHessian()
    def printPars(self):
        stmp="  %13s: %s\n"
        ftmp="  %13s: %7.4f\n"
        itmp="  %13s: %7d\n"
        self.out.write('')
        self.out.write(itmp%('Algorithm',self.algorithm))
        self.out.write(itmp%('N. Points',self.npoints))
        self.out.write(ftmp%('Grad. Tol.',self.tolerance))
        self.out.write('')
        self.out.write(stmp%('Hessian',self.hessfn))
        self.out.write(itmp%('Mode',self.mode))
        self.out.write(itmp%('Direction',self.direction))
        self.out.write('')
        self.out.write(ftmp%('Alpha',self.alpha))
        self.out.write(ftmp%('Delta',self.delta))
        self.out.write('')
        self.out.write(ftmp%('Damp Factor',self.damp))
        self.out.write(itmp%('Damp Update',self.autodamp))
        self.out.write('')
        self.out.write(ftmp%('Max. Displ.',self.maxdispl))
        self.out.write('')
        self.out.write(stmp%('Guess',self.guessfn))
        self.out.write("\n------------------------------------------------\n")
    def ReadInput(self,json_input):
        # Read in input from JSON input file
        json_data=open(json_input).read()
        input_params = json.loads(json_data)
        if input_params['molecule']['geometry']:
            self.geometry = JSON2XYZ(input_params)
        if input_params['model']['basis']:
            self.basis = input_params['model']['basis']
            self.level_of_theory = "%s/%s" %(self.method,self.basis)
            #print("IN HERE")
        if input_params['model']['method']:
            self.method = input_params['model']['method']
            self.level_of_theory = "%s/%s" %(self.method,self.basis)
        if input_params['molecule']['symbols']: 
            self.natoms = len(input_params['molecule']['symbols'])
        if input_params['keywords']:
            self.keywords = input_params['keywords']
        if "irc" in input_params:
            if input_params['irc']['hessfile']:
                self.hessfn = input_params['irc']['hessfile']
            if input_params['irc']['guess']:
                self.guessfn = input_params['irc']['guess']
            if input_params['irc']['alpha']:
                self.alpha = input_params['irc']['alpha']
            if input_params['irc']['delta']:
                self.delta = input_params['irc']['delta']
            if input_params['irc']['damp']:
                self.damp = input_params['irc']['damp']
            if input_params['irc']['restart']:
                if(input_params['irc']['restart']==1):
                    self.restart = True
                else:
                    self.restart = False
            if input_params['irc']['autodamp']:
                if(input_params['irc']['autodamp']==1):
                    self.autodamp=True
                else:
                    self.autodamp=False
            if input_params['irc']['tol']:
                self.tolerance= input_params['irc']['tol']
            if input_params['irc']['alg']:
                self.algorithm = input_params['irc']['alg']
            if input_params['irc']['dir']:
                self.direction = input_params['irc']['dir']
            if input_params['irc']['mode']:
                self.mode = input_params['irc']['mode']
            if input_params['irc']['maxd']:
                self.maxdispl = input_params['irc']['maxd']
            if input_params['irc']['pts']:
                self.npoints = input_params['irc']['pts']
        else: 
            pass
   # def JSON2XYZ(self, input_params):
   #     geom = ''
   #     geom += '%d ' %input_params['molecule']['molecular_charge']
   #     geom += '%d \n' %input_params['molecule']['molecular_multiplicity'] 
   #     symbols = input_params['molecule']['symbols']
   #     geometry = input_params['molecule']['geometry']
   #     for i in range(len(symbols)):
   #         geom += "%s  " %symbols[i]
   #         for j in range(3):
   #             if(j==2):
   #                 geom += "   %f   \n" %geometry[(i + 2*i) + j]
   #             else:
   #                 geom += "   %f   " %geometry[(i + 2*i) + j]
   #     self.geom = geom	

    def ComputeHessian(self):
        # Use PSI4 to calculate Hessian matrix
        psi4.core.set_output_file("hessian.out", False)
        psi4.geometry(self.geometry)
        #print(self.keywords)
        psi4.set_options(self.keywords)
        H = psi4.hessian(self.method)
        Hess = np.array(H)
        print(Hess.shape)
        self.displacement = Hess[:,self.mode]
        print(self.displacement.shape)
        self.grad = np.zeros(3*self.natoms) 


##########################
# Energies and Gradients #
##########################

def doEnergy(geom,pars):
    psi4.geometry(geom)
    E = psi4.energy(pars.level_of_theory)
    return E

def doGrad(geom,pars):
    psi4.geometry(geom)
    Grad, wfn = psi4.gradient(pars.level_of_theory, return_wfn=True)
    e = wfn.energy()
    G = np.array(Grad)
    print(G.shape)
    pars.grad = G
    return G, e


######################################
# Geometry manipulation and printing #
######################################

def geodisplace(geom, displace):
    new_geom = []
    displaced_geom = ''
    symbols = []
    #print(geom)
    lines = geom.split('\n')
    lines.pop(0)
    del lines[-1]
    charge_mult_line = lines[0].split() #Extract the Charge and Multiplicity from top of string
    charge = int(charge_mult_line[0])
    mult = int(charge_mult_line[1])
    for line in lines[1:]: # Loop Over lines that actually contain atoms
        atom_line = line.split()
        #print(atom_line)
        symbols.append(atom_line[0])
        atom_line.pop(0) # Get rid of atom symbol temporarily
        new_geom.append(list(map(float,atom_line)))
    i=0
    for atom in new_geom:
        atom[0] += displace[i]
        atom[1] += displace[i+1]
        atom[2] += displace[i+2]
        i += 3
#TODO (12/15/18) Finish this, all we have to do is transform the geometry from a list to a
#string like the geometry given as an input to this function.
    displaced_geom += "\n%d %d\n" %(charge, mult)
    for i in range(len(symbols)):
        displaced_geom += "%s  " %symbols[i]
        for j in range(3):
            if(j==2):
                #displaced_geom += "   %f   \n" %new_geom[(i + 2*i) + j]
                displaced_geom += "   %f   \n" %new_geom[i][j]
            else:
                #displaced_geom += "   %f   " %new_geom[(i + 2*i) + j]
                displaced_geom += "   %f   " %new_geom[i][j]
    print(displaced_geom)
    return displaced_geom

def printTrj(params, n):
    trajectory_file = open(params.basename+'.trj', 'a')
    trajectory_file.write("%d\npyREX IRC point %d E=%14.7f\n"%(params.natoms,n,params.energy))
    trajectory_file.write("%s\n" %params.geometry)
    trajectory_file.close()

###############
#IRC Functions#
###############

def Morokuma(pars,start=False):
    #Does a cycle in the Morokuma algorithm, returns the energy and MaxGrad of the
    # new point
    if (start):
        #apply the appropriate sign to the displacement and convert to angs.
        pars.displacement=float(pars.direction)*pars.displacement
        #for i in range(len(pars.mass)):
        #   pars.displacement[(3*i)] /= np.sqrt(pars.mass[i])
        #   pars.displacement[(3*i)+1] /= np.sqrt(pars.mass[i])
        #   pars.displacement[(3*i)+2] /= np.sqrt(pars.mass[i])
        pars.displacement=pars.alpha*(pars.displacement/np.linalg.norm(pars.displacement))
        #Eo,MGo = doGrad(pars.geometry, pars)
        #tmpvec0=pars.grad
        #displace geometry following the normal mode
        geo1=geodisplace(pars.geometry,pars.displacement)
        E1,MG1=doGrad(geo1,pars)
        #generate vector D, adapting from eq 6 in J. Chem. Phys. 66, 2153
        tmpvec1=pars.grad
        D=-(tmpvec0/np.linalg.norm(tmpvec0))+(tmpvec1/np.linalg.norm(tmpvec1))
        #D=(pars.displacement/np.linalg.norm(pars.displacement))-(tmpvec/np.linalg.norm(tmpvec))
    else:
        #scale down gradients and calculate the displacement
        pars.displacement=(pars.damp*pars.displacement)-((1.0-pars.damp)*pars.grad)
        for i in range(len(pars.mass)):
            pars.displacement[(3*i)] /= np.sqrt(pars.mass[i])
            pars.displacement[(3*i)+1] /= np.sqrt(pars.mass[i])
            pars.displacement[(3*i)+2] /= np.sqrt(pars.mass[i])
        pars.displacement=pars.maxdispl*(pars.displacement/np.linalg.norm(pars.displacement))
        #displace geometry following the gradient
        geo1=geodisplace(pars.geometry,pars.displacement)
        E1,MG1=doGrad(geo1,pars)
        #generate vector D, adapting from eq 6 in J. Chem. Phys. 66, 2153
        tmpvec=pars.grad
        D=(pars.displacement/np.linalg.norm(pars.displacement))-(tmpvec/np.linalg.norm(tmpvec))
    # find the optimum delta that will assure the new point is at the
    # local minimum
    if (pars.algorithm==1):
        geo2=geodisplace(geo1,pars.delta*D)
        E2=doEnergy(geo2,pars)
        if (E2>E1):
            newdelta=0.5*pars.delta
        else:
            newdelta=2.0*pars.delta
        geo3=geodisplace(geo1,newdelta*D)
        E3=doEnergy(geo3,pars)
        Evals=np.array([E1, E2, E3])
        Deltavals=np.array([0.0,pars.delta,newdelta])
    else:
        geo2=geodisplace(geo1,pars.delta*D)
        E2=doEnergy(geo2,pars)
        delta3=0.5*pars.delta
        geo3=geodisplace(geo1,delta3*D)
        E3=doEnergy(geo3,pars)
        delta4=2.0*pars.delta
        geo4=geodisplace(geo1,delta4*D)
        E4=doEnergy(geo4,pars)
        delta5=-0.5*pars.delta
        geo5=geodisplace(geo1,delta5*D)
        E5=doEnergy(geo5,pars)
        Evals=np.array([E1, E2, E3, E4, E5])
        Deltavals=np.array([0.0,pars.delta,delta3, delta4, delta5])
    deltaFit=np.polyfit(Deltavals,Evals,deg=2)
    opdelta=-(deltaFit[1]/(2.0*deltaFit[0]))
    # update the geometry to the new point, update and return energy and gradients
    pars.geos.append(pars.geometry)
    pars.energies.append(pars.energy)
    pars.geometry=geodisplace(geo1,opdelta*D)
    newE, newMaxGrad = doGrad(pars.geometry,pars)
    pars.energy=newE
    #the following line is just for debugging purposes
    #print(Evals, Deltavals,np.linalg.norm(pars.displacement), opdelta)
    return (newE, newMaxGrad)

def ircdrv(inpname):
    params=ToolKit(inpname)
    params.out.write("""   IRC wrapper for Orca - version 2.0
   by Filipe Teixeira,
   REQUIMTE
   Faculdade de Ciencias da Universidade do Porto

  Using Orca from: %s

  Parameters for this run: \n"""%(params.orcacmd))
    params.printPars()
    #print(params.geometry)
    keep=True
    n=0
    oldE=0.0
    params.out.write("   Pt. %20s %9s %10s\n"%('Energy','RMS Grad.','Damp'))
    params.out.write("------------------------------------------------\n")
    while (keep):
        if (params.restart or (n>0)):
            E,MG=Morokuma(params,False)
        else:
            E,MG=Morokuma(params,True)
        n=n+1
        if(params.autodamp and (n>1)):
            params.damp = params.damp * (0.1/np.log(n))
            if (params.damp<1.0e-5):
                params.damp=0.0
                params.autodamp=False
        params.out.write('@  %3d %20.9f %9.5f %10.2e\n'%(n, E, MG, params.damp))
        if (n>params.npoints):
            keep=False
            printTrj(params,n) #appends newGeo
            params.out.write("----------------------------------------------\n")
            params.out.write("--          IRC CALCULATION ENDED           --\n")
            params.out.write("--             MAXPTS ACHIEVED!             --\n")
            params.out.write("----------------------------------------------\n")
        elif (MG<params.tolerance):
            keep=False
            printTrj(params,n) #appends newGeo
            params.out.write("----------------------------------------------\n")
            params.out.write("--          IRC CALCULATION ENDED           --\n")
            params.out.write("--              TOL ACHIEVED!               --\n")
            params.out.write("----------------------------------------------\n")
        elif (E>oldE):
            keep=False
            #printTrj(params,n) #appends newGeo
            params.out.write("----------------------------------------------\n")
            params.out.write("--             ENERGY INCREASED             --\n")
            params.out.write("--            GEOMETRY  MIGHT BE            --\n")
            params.out.write("--          VERY CLOSE TO A MINIMUM         --\n")
            params.out.write("--                                          --\n")
            params.out.write("--        IRC CALCULATION TERMINATED!       --\n")
            params.out.write("----------------------------------------------\n")
        else:
            printTrj(params,n) #appends newGeo
            oldE=E
    params.out.close()

if __name__=='__main__':
    if(len(sys.argv)!=2):
        print("""IRC4Orca - Version 2.0
An Implementation of Morokuma's IRC method for the Orca ESS Software.
by Filipe Teixeira

Usage: %s file.inp

Please consult https://github.com/teixeirafilipe/irc4orca for more information.

"""%(sys.argv[0]))
        sys.exit(1)
    ircdrv(sys.argv[1])
 
