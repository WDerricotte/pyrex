# Helper "Library" to compute Molecular Dynamics (MD) Trajectories
# Numpy and OS python modules are required
#
# MD and Velocity Verlet Algorithms were taken from: :
# Computational Soft Matter:  From Synthetic Polymers to Proteins, Lecture Notes,
# Norbert Attig, Kurt Binder, Helmut Grubmuller, Kurt Kremer (Eds.),
# John von Neumann Institute for Computing, Julich,
# NIC Series, Vol. 23, ISBN 3-00-012641-4, pp. 1-28, 2004
#
# Created by: Leonardo dos Anjos Cunha
# Date: 05/16/17
# License: GPL v3.0

import psi4
import numpy as np
import os

# Converting Atomic Mass Unit (amu) to atomic units (au)
amu2au = 1822.8884850
bohr2ang = 0.529177
ang2bohr = 1.88973
au2amu = 5.485799097e-4

def md_trajectories(max_md_step):
    """ Creates single .xyz file with MD Trajectories with all points.
        
        Parameters:
        ----------
            int max_md_steps -- Number of MD steps calculated

        Returns:
        -------
            file md_trajectories.xyz -- File containing all the trajectory points for visualization
    """

    with open('md_trajectories.xyz','w') as outfile:
      for i in range(1,max_md_step+1):
        with open('md_step_'+str(i)+'.xyz')as infile:
            outfile.write(infile.read())
    os.system('rm md_step*')

def integrator(int_alg,timestep,pos,veloc,accel,molec,grad_method,symbols,opt):
    """ Selects the type of integration algorithm to propagate the trajectories
        Only velocity Verlet implemented (date: 05/23/17 - LAC)

        Parameters:
        ----------
            string int_alg --  Integrator Algorith to be used
                Options:
                a) veloc_verlet --  Use Velocity Verlet Algorithm
            float timestep -- Time step to be used on the MD trajectory propagation step
            array pos --  Numpy array (natoms,3) with old positions/trajectories
            array veloc --  Numpy array (natoms,3) with old velocities
            array accel -- Numpy array (natoms,3) with old accelerations
            psi4_object molec --  Psi4 molecule object to be used
            string grad_method: Method to be used to calculate energies and forces

        Returns:
        -------
            array pos_new -- Numpy array (natoms,3) with the updated positions
            array vel_new -- Numpy array (natoms,3) with the updated velocities
            array accel_new -- Numpy array (natoms,3) with the updated accelerations
            float E -- Updated energy of the system
    """

    natoms = molec.natom()
    atom_mass = np.asarray([molec.mass(atom) for atom in range(natoms)])*amu2au

    # Velocity Verlet Integrator
    if int_alg=='veloc_verlet':
        #vel_new =  veloc+0.5*timestep*accel
        pos = np.array(pos)
        print(pos)
        veloc = np.array(veloc)
        accel = np.array(accel)
        if(opt):
            pos_new =  pos + 0.1*accel # If Opt, just add the gradient 
        else:
            pos_new =  pos + timestep*veloc + 0.5*accel*(timestep**2.0)
        #print(pos_new)
        geom_string = "\n%d %d\n" %(molec.molecular_charge(), molec.multiplicity())
        for i in range(natoms):
            #print(symbols)
            geom_string += "%s  " %symbols[i]
            for j in range(3):
                if(j==2):
                    geom_string += "   %f   \n" %((pos_new[i][j]))
                else:
                    geom_string += "   %f   " %((pos_new[i][j]))
        molec.set_geometry(psi4.core.Matrix.from_array(pos_new))
        #molec.set_units(psi4.core.GeometryUnits.Bohr)
        geom_string += "symmetry c1\n"
        geom_string += "no_reorient\n"
        geom_string += "no_com\n"
        geom_string += "units bohr"
        psi4.geometry(geom_string)
        E,force_new = get_forces(grad_method)
        print(force_new)
        if(opt):
            accel_new = force_new/(np.ones((natoms,1))) #If Opt, don't mass weight gradient
        else:
            accel_new = force_new/((atom_mass.reshape((natoms,1))))
        print(atom_mass.reshape((natoms,1)))
        vel_new = veloc + 0.5*(accel + accel_new)*timestep
    return pos_new,vel_new,accel_new,E

def damp_velocity(velocity, params):
    """ Damps the velocity such that the magnitude of the velocity vector is constant,
        the constant velocity is a parameter provided by the user. (See Eq. 4 in 
        J. Phys. Chem. A 2002, 106, 165-169)
    """
    vel_norm = np.linalg.norm(velocity)
    damping_factor = params.cons_vel/vel_norm
    damped_velocity = damping_factor*velocity
    return damped_velocity

def get_forces(grad_method):
    """ Selects the method (QC or FF) to be used to calculate energies and forces for the system
        Only Psi4 supported methods implemented (date: 05/23/17 - LAC)
    
        Parameters:
        ----------
            string grad_method -- Method to be used to calculate forces and energies

        Returns:
        -------
            float E -- Energy of the system
            array force -- Numpy array (natoms,3) containing the forces acting on each atom of the system
    """
    psi4.core.set_output_file("psi4_out.dat", False)
    #psi4.set_options({"d_convergence" : 0})
    E,wfn = psi4.energy(grad_method,return_wfn=True)
    force = -np.asarray(psi4.gradient(grad_method,ref_wfn=wfn))
    return E,force
