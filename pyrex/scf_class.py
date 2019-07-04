"""
Base class to run SCF calculations
"""

import time
import os
import subprocess
import numpy as np
import psi4
from pyscf import lib
from pyscf import scf, dft ,gto, solvent
from pyscf.solvent import ddcosmo

class scf_class(object):

    def __init__(self,data,outfile):
        self.level_of_theory = "%s/%s" %(data.method,data.basis)
        self.charge = data.molecular_charge
        self.coordinates = data.coordinates
        self.mult = data.molecular_multiplicity
        self.nthreads = data.nthreads
        self.do_solvent = data.do_solvent
        self.eps = data.eps
        self.basis = str(data.basis)
        self.outfile = outfile
        self.keywords = data.keywords

   # def psi4_molden(self, geometries):
   #     """
   #     Function to produce Molden files for key structures along reaction coordinate
   #     """
   #     struct_titles = ["r", "f_min", "ts", "f_max", "p"]
   #     i = 0
   #     for geometry in geometries:
   #         psi4.core.set_output_file("%s.out" %struct_titles[i], False)
   #         geom = geometry
   #         # Code Related to JSON testing #
   #         #geom_parse = geom.split()
   #         #del geom_parse[0:2] #Remove Charge and Multiplicity 
   #         #print(geom_parse)
   #         geom += "symmetry c1"
   #         mol = psi4.geometry(geom)
   #         psi4.set_options(self.keywords)
   #         #print("pyREX:Single Point Calculation on IRC Point %d" %(count))
   #         psi4.set_num_threads(self.nthreads)
   #         energy, wfn = psi4.energy(self.level_of_theory, return_wfn=True)
   #         d = wfn.Da().to_array()
   #         s = wfn.S().to_array()
   #         c = wfn.Ca().to_array()
   #         occs = c.T.dot(s.dot(d).dot(s).dot(c))
   #         psi4.driver.molden(wfn, "%s.molden" %struct_titles[i], density_a = psi4.core.Matrix.from_array(occs))
   #         #TODO:This now prints molden files for each key structure, now how can we
   #         #     add JANPA functionality to this?
   #         #subprocess.call(['java', '-jar', '/root/wderricotte/src/janpa/molden2molden.jar', '-NormalizeBF', '-cart2pure', '-i', '%s.molden' %struct_titles[i], '-o', '%s_conv.molden' %struct_titles[i]])
   #         #log_file = open('%s_janpa.log' %struct_titles[i], 'w+')
   #         #subprocess.call(['java', '-jar', '/root/wderricotte/src/janpa/janpa.jar', '-i', '%s_conv.molden' %struct_titles[i], '-CLPO_Molden_File', '%s_CLPO.molden' %struct_titles[i]], stdout=log_file)
   #         #log_file.close()
   #         #i = i+1

    def psi4_scf(self, geometries):
        """
        Function to run SCF along IRC using PSI4, returns array of energies at each geometry. 
        """
        output = open(self.outfile, "a")
        output.write('\n\n--Reaction Energy--\n')
        output.write('\n-------------------------------------------------------------------------------------')
        output.write('\n{:>20} {:>20} {:>20} {:>20}\n'.format('IRC Point', 'E (Hartree)', 'HOMO (a.u.)','LUMO (a.u.)'))
        output.write('-------------------------------------------------------------------------------------\n')
        output.close()
        energies = []
        wavefunctions = []
        count = 0
        start = time.time()
        for geometry in geometries:
            output = open(self.outfile, "a")
            psi4.core.set_output_file("psi4_output/irc_%d.out" %count, False)
            geom = geometry
            # Code Related to JSON testing #
            #geom_parse = geom.split()
            #del geom_parse[0:2] #Remove Charge and Multiplicity 
            #print(geom_parse)
            geom += "symmetry c1"
            mol = psi4.geometry(geom)
            psi4.set_options(self.keywords)
            #print("pyREX:Single Point Calculation on IRC Point %d" %(count))
            psi4.set_num_threads(self.nthreads)
            energy, wfn = psi4.energy(self.level_of_theory, return_wfn=True)
            #wfn = psi4.core.Wavefunction.build(mol, self.basis)
            ndocc = wfn.doccpi()[0]
            #print(ndocc)
            eps = np.array(wfn.epsilon_a())
            #print(eps)
            homo_energy = eps[ndocc - 1]
            lumo_energy = eps[ndocc]
            energies.append(energy)
            wavefunctions.append(wfn)
            output.write('{:>20.2f} {:>20.4f} {:>20.4f} {:>20.4f}\n'.format(self.coordinates[count], energy, homo_energy, lumo_energy))
            count = count+1
            output.close()
        output = open(self.outfile, "a")
        output.write('-------------------------------------------------------------------------------------\n')
        output.close()
        end = time.time()
        print("psi4 Time = %f" %(end - start))
        return energies, wavefunctions

    def pyscf_scf(self, geometries):
        """
        Function to run SCF along IRC using pySCF, returns array of energies at each geometry.
        """
        if(os.path.isdir('pyscf_output')):
            pass
        else:
            os.makedirs("pyscf_output")
        output = open(self.outfile, "a")
        output.write('\n\n--Reaction Energy--\n')
        output.write('\n-------------------------------------------------------------------------------------')
        output.write('\n{:>20} {:>20} {:>20} {:>20}\n'.format('IRC Point', 'E (Hartree)', 'HOMO (a.u.)','LUMO (a.u.)'))
        output.write('-------------------------------------------------------------------------------------\n')
        output.close()
        energies = []
        frontier_orb_energies = []
        count = 0
        start = time.time()
        lib.num_threads(self.nthreads)
        for geometry in geometries:
            output = open(self.outfile, "a")
            mol = gto.Mole()
            mol.output = 'pyscf_output/irc_%d.dat' %count
            mol.verbose = 0
            mol.atom = geometry
            mol.basis = self.basis
            mol.charge = self.charge
            mol.spin = self.mult - 1
            mol.build() 
            scf_obj = scf.RHF(mol)
            if(self.do_solvent):
                solv_obj = ddcosmo.ddcosmo_for_scf(scf_obj)
                solv_obj.with_solvent.eps = self.eps
                solv_cosmo = solvent.ddCOSMO(solv_obj)
                energy = solv_cosmo.scf()
                mo_e = solv_cosmo.mo_energy
                nocc = np.count_nonzero(solv_cosmo.mo_occ)
                nocc = np.count_nonzero(solv_cosmo.mo_occ)
                homo_energy = mo_e[nocc - 1]
                lumo_energy = mo_e[nocc]
                homo_lumo = (homo_energy,lumo_energy)
            else:
                energy = scf_obj.scf()
                mo_e = scf_obj.mo_energy
                nocc = np.count_nonzero(scf_obj.mo_occ)
                homo_energy = mo_e[nocc - 1]
                lumo_energy = mo_e[nocc]
                homo_lumo = (homo_energy,lumo_energy)
            frontier_orb_energies.append(homo_lumo)
            energies.append(energy)
            output.write('{:>20.2f} {:>20.4f} {:>20.4f} {:>20.4f}\n'.format(self.coordinates[count], energy, homo_energy, lumo_energy))
            count = count+1
            output.close()
        output = open(self.outfile, "a")
        output.write('-------------------------------------------------------------------------------------\n')
        output.close()
        end = time.time()
        print("pySCF Time = %f" %(end - start)) 
        return energies,frontier_orb_energies

    def pyscf_dft(self, geometries, xc_functional):
        """
        Function to run DFT along IRC using pySCF, returns array of energies at each geometry.
        """
        if(os.path.isdir('pyscf_output')):
            pass
        else:
            os.makedirs("pyscf_output")
        output = open(self.outfile, "a")
        output.write('\n\n--Reaction Energy--\n')
        output.write('\n-------------------------------------------------------------------------------------')
        output.write('\n{:>20} {:>20} {:>20} {:>20}\n'.format('IRC Point', 'E (Hartree)', 'HOMO (a.u.)','LUMO (a.u.)'))
        output.write('-------------------------------------------------------------------------------------\n')
        output.close()
        energies = []
        frontier_orb_energies = []
        count = 0
        start = time.time()
        lib.num_threads(self.nthreads)
        for geometry in geometries:
            output = open(self.outfile, "a")
            mol = gto.Mole()
            mol.output = 'pyscf_output/irc_%d.dat' %count
            mol.verbose = 0
            mol.atom = geometry
            mol.basis = self.basis
            mol.charge = self.charge
            mol.spin = self.mult - 1
            mol.build()
            dft_obj = dft.RKS(mol)
            dft_obj.xc = xc_functional
            if(self.do_solvent):
                solv_obj = ddcosmo.ddcosmo_for_scf(dft_obj)
                solv_obj.with_solvent.eps = self.eps
                solv_cosmo = solvent.ddCOSMO(solv_obj)
                energy = solv_cosmo.scf()
                mo_e = solv_cosmo.mo_energy
                nocc = np.count_nonzero(solv_cosmo.mo_occ)
                nocc = np.count_nonzero(solv_cosmo.mo_occ)
                homo_energy = mo_e[nocc - 1]
                lumo_energy = mo_e[nocc]
                homo_lumo = (homo_energy,lumo_energy)
            else:
                energy = dft_obj.scf()
                mo_e = dft_obj.mo_energy
                nocc = np.count_nonzero(dft_obj.mo_occ)
                homo_energy = mo_e[nocc - 1]
                lumo_energy = mo_e[nocc]
                homo_lumo = (homo_energy,lumo_energy)
            frontier_orb_energies.append(homo_lumo)
            energies.append(energy)
            output.write('{:>20.2f} {:>20.4f} {:>20.4f} {:>20.4f}\n'.format(self.coordinates[count], energy, homo_energy, lumo_energy))
            count = count+1
            output.close()
        output = open(self.outfile, "a")
        output.write('-------------------------------------------------------------------------------------\n')
        output.close()
        end = time.time()
        print("pySCF Time = %f" %(end - start))
        return energies,frontier_orb_energies

    def opt(self, label, natoms, geom):
        """
        Optimizes individual fragments for strain energy calculations.
        """
        output = open(self.outfile, "a")
        frag = ""
        geom = geom.split('\n')[:(natoms+2)]
        for i in range(natoms+2):
            frag += "%s\n" %geom[i]
        frag += "symmetry c1"
        print("Geometry Optimization on Fragment %s" %label)
        psi4.set_options(self.keywords)
        psi4.geometry(frag)
        psidump = "psi4_output/fragment_%s_opt.out" %label
        psi4.core.set_output_file(psidump, False)
        psi4.set_num_threads(self.nthreads)
        e = psi4.optimize(self.level_of_theory)
        #psi4.core.clean()
        return e
