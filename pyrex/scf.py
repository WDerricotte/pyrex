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
import orca_interface
import sparrow_interface

def print_header(outfile):
    output = open(outfile, "a")
    output.write('\n\n--Reaction Energy--\n')
    output.write('\n-------------------------------------------------------------------------------------')
    output.write('\n{:>20} {:>20} {:>20} {:>20}\n'.format('IRC Point', 'E (Hartree)', 'HOMO (a.u.)','LUMO (a.u.)'))
    output.write('-------------------------------------------------------------------------------------\n')
    output.close()

def psi4_scf(params, geometries):
    """
    Function to run SCF along IRC using PSI4, returns array of energies at each geometry. 
    """
    print_header(params.outfile)
    energies = []
    wavefunctions = []
    count = 0
    start = time.time()
    level_of_theory = "%s/%s" %(params.method,params.basis)
    if(params.do_solvent):
        set_solvent_parameters(params)
    for geometry in geometries:
        output = open(params.outfile, "a")
        psi4.core.set_output_file("psi4_output/irc_%d.out" %count, False)
        geom = geometry
        geom += "\nsymmetry c1"
        mol = psi4.geometry(geom)
        psi4.set_options(params.keywords)
        #print("pyREX:Single Point Calculation on IRC Point %d" %(count))
        psi4.set_num_threads(params.nthreads)
        if(params.set_memory):
                psi4.set_memory(params.memory_allocation)
        energy, wfn = psi4.energy(level_of_theory, return_wfn=True)
        #wfn = psi4.core.Wavefunction.build(mol, self.basis)
        ndocc = wfn.doccpi()[0]
        #print(ndocc)
        eps = np.array(wfn.epsilon_a())
        #print(eps)
        homo_energy = eps[ndocc - 1]
        lumo_energy = eps[ndocc]
        energies.append(energy)
        wavefunctions.append(wfn)
        output.write('{:>20.2f} {:>20.4f} {:>20.4f} {:>20.4f}\n'.format(params.coordinates[count], energy, homo_energy, lumo_energy))
        count = count+1
        output.close()
    print_footer(params.outfile)
    end = time.time()
    print("psi4 Time = %f" %(end - start))
    return energies, wavefunctions

def sparrow_scf(params, geometries):
    energies = []
    count = 0
    for geometry in geometries:
        sparrow_struct = open("sparrow_inp%d.xyz" %count, "w+")
        sparrow_output = open("output_%d.dat" %count, "w+")
        sparrow_output.close()
        sparrow_struct.write("%d\n" %params.natoms)
        sparrow_struct.write("Sparrow Structure Generated by PYREX\n")
        sparrow_geom = geometry[5:]
        sparrow_struct.write(sparrow_geom)
        sparrow_struct.close()
        sparrow_interface.run_sparrow("sparrow_inp%d.xyz" %count,
        params.charge,params.mult, params.method,"output_%d.dat" %count, "")
        e = sparrow_interface.sparrow_energy("output_%d.dat" %count)
        energies.append(e)
        count = count + 1
    return energies 


def orca_scf(params, geometries):
    """
    Function to run SCF along IRC using ORCA, returns array of energies at each geometry.
    """
    print_header(params.outfile)
    input_header = "!%s %s %s" %(params.method,params.basis,params.orca_header)
    frontier_orb_energies = []
    energies = []
    count = 0
    for geometry in geometries:
        energy = 0.0
        homo_energy = 0.0
        lumo_energy = 0.0
        orca_input = input_header
        orca_input += "\n%s" %params.orca_block
        orca_input += "\n%s" %geometry
        cwd = os.getcwd() 
        orca_output = orca_interface.run_orca(orca_input=orca_input, jobname="orca_job_%d" %count, output_root_dir="%s/orca_output" %cwd, overwrite=True)
        orca_out = iter(orca_output.output_lines())
        for line in orca_out:
            if("FINAL SINGLE POINT ENERGY" in line):
                energy = float(line.split()[4])
            if("Number of Electrons" in line):
                nelec = int(line.split()[5])
                homo_num = int(nelec/2)
                lumo_num = int(homo_num + 1)
            if("OCC" in line):
                for i in range(homo_num):
                    line = next(orca_out)
                homo_energy = float(line.split()[2])
                line = next(orca_out)
                lumo_energy = float(line.split()[2])
        homo_lumo = (homo_energy,lumo_energy)
        frontier_orb_energies.append(homo_lumo)
        energies.append(energy)
        output = open(params.outfile, "a")
        output.write('{:>20.2f} {:>20.4f} {:>20.4f} {:>20.4f}\n'.format(self.coordinates[count], energy, homo_energy, lumo_energy))
        count = count+1
        output.close()
    print_footer(params.outfile)
    return energies,frontier_orb_energies 

def pyscf_scf(params, geometries):
    """
    Function to run SCF along IRC using pySCF, returns array of energies at each geometry.
    """
    if(os.path.isdir('pyscf_output')):
        pass
    else:
        os.makedirs("pyscf_output")
    print_header(params.outfile)
    energies = []
    frontier_orb_energies = []
    count = 0
    start = time.time()
    lib.num_threads(params.nthreads)
    for geometry in geometries:
        output = open(params.outfile, "a")
        mol = gto.Mole()
        mol.output = 'pyscf_output/irc_%d.dat' %count
        mol.verbose = 0
        mol.atom = geometry
        mol.basis = params.basis
        mol.charge = params.molecular_charge
        mol.spin = params.molecular_multiplicity - 1
        mol.build() 
        scf_obj = scf.RHF(mol)
        if(params.do_solvent):
            solv_obj = set_solvent_parameters(params, scf_obj)
            df = solv_obj.density_fit()
        else:
            df = scf_obj.density_fit()
        energy = df.scf()
        mo_e = df.mo_energy
        nocc = np.count_nonzero(df.mo_occ)
        homo_energy = mo_e[nocc - 1]
        lumo_energy = mo_e[nocc]
        homo_lumo = (homo_energy,lumo_energy)
        frontier_orb_energies.append(homo_lumo)
        energies.append(energy)
        output.write('{:>20.2f} {:>20.4f} {:>20.4f} {:>20.4f}\n'.format(params.coordinates[count], energy, homo_energy, lumo_energy))
        count = count+1
        output.close()
    print_footer(params.outfile)
    end = time.time()
    print("pySCF Time = %f" %(end - start)) 
    return energies,frontier_orb_energies

def pyscf_dft(params, geometries, xc_functional):
    """
    Function to run DFT along IRC using pySCF, returns array of energies at each geometry.
    """
    if(os.path.isdir('pyscf_output')):
        pass
    else:
        os.makedirs("pyscf_output")
    print_header(params.outfile)
    energies = []
    frontier_orb_energies = []
    count = 0
    start = time.time()
    lib.num_threads(params.nthreads)
    for geometry in geometries:
        output = open(params.outfile, "a")
        mol = gto.Mole()
        mol.output = 'pyscf_output/irc_%d.dat' %count
        mol.verbose = 0
        mol.atom = geometry
        mol.basis = params.basis
        mol.charge = params.molecular_charge
        mol.spin = params.molecular_multiplicity - 1
        mol.build()
        dft_obj = dft.RKS(mol)
        dft_obj.xc = xc_functional
        if(params.do_solvent):
            solv_obj = set_solvent_parameters(params, dft_obj)
            df = solv_obj.density_fit()
        else:
            df = dft_obj.density_fit()
        energy = df.scf()
        mo_e = df.mo_energy
        nocc = np.count_nonzero(df.mo_occ)
        homo_energy = mo_e[nocc - 1]
        lumo_energy = mo_e[nocc]
        homo_lumo = (homo_energy,lumo_energy)
        frontier_orb_energies.append(homo_lumo)
        energies.append(energy)
        output.write('{:>20.2f} {:>20.4f} {:>20.4f} {:>20.4f}\n'.format(params.coordinates[count], energy, homo_energy, lumo_energy))
        count = count+1
        output.close()
    print_footer(params.outfile)
    end = time.time()
    print("pySCF Time = %f" %(end - start))
    return energies,frontier_orb_energies

def opt(params, label, natoms, geom):
    """
    Optimizes individual fragments for strain energy calculations.
    """
    level_of_theory = "%s/%s" %(params.method,params.basis)
    output = open(params.outfile, "a")
    frag = ""
    geom = geom.split('\n')[:(natoms+2)]
    for i in range(natoms+2):
        frag += "%s\n" %geom[i]
    frag += "symmetry c1"
    print("Geometry Optimization on Fragment %s" %label)
    psi4.set_options(params.keywords)
    psi4.geometry(frag)
    psidump = "psi4_output/fragment_%s_opt.out" %label
    psi4.core.set_output_file(psidump, False)
    psi4.set_num_threads(params.nthreads)
    e = psi4.optimize(level_of_theory)
    #psi4.core.clean()
    return e

def set_solvent_parameters(params, scf_obj=None):
    if(params.qm_program=="psi4"):
        psi4.pcm_helper("""
            Units = Angstrom
            Medium {
            SolverType = IEFPCM
            Solvent = %s
            }
            Cavity {
            RadiiSet = UFF
            Type = GePol
            Scaling = False
            Area = 0.3
            Mode = Implicit
            }
        """ %params.pcm_solvent)
        params.keywords['pcm'] = "true"
        params.keywords['pcm_scf_type'] = "total"
    if(params.qm_program=="pyscf"):
        solv_obj = scf_obj.DDCOSMO()
        solv_obj.with_solvent.eps = params.eps
        scf_obj = solv_obj
    return scf_obj

def print_footer(outfile):
    output = open(outfile, "a")
    output.write('-------------------------------------------------------------------------------------\n')
    output.close()
