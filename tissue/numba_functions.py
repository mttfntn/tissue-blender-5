# SPDX-FileCopyrightText: 2019-2022 Blender Foundation
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Numba versions of the slowest loops (Tessellate interpolation and thickness,
Reaction-Diffusion). They exist only when Numba can be imported (bool_numba):
the callers check for them and fall back to NumPy otherwise.
"""

import numpy as np
import time
import sys

bool_numba = False

try:
    from .utils_pip import Pip
    Pip._ensure_user_site_package()
    from numba import jit, njit, guvectorize, float64, int32, prange
    from numba.typed import List
    bool_numba = True
except:
    pass

if bool_numba:
    #from numba import jit, njit, guvectorize, float64, int32, prange


    @njit(parallel=True)
    #@cuda.jit('void(float32[:,:], float32[:,:])')
    def tex_laplacian(lap, arr):
        arr2 = arr*2
        diag = sqrt(2)/2
        nx = arr.shape[0]
        ny = arr.shape[1]
        for i in prange(nx):
            for j in prange(ny):
                i0 = (i-1)%nx
                j0 = (j-1)%ny
                i1 = (i+1)%nx
                j1 = (j+1)%ny
                #lap[i+1,j+1] = arr[i, j+1] + arr[i+2, j+1] + arr[i+1, j] + arr[i+1, j+2] - 4*arr[i+1,j+1]

                lap[i,j] = ((arr[i0, j] + arr[i1, j] - arr2[i,j]) + \
                               (arr[i, j0] + arr[i, j1] - arr2[i,j]) + \
                               (arr[i0, j0] + arr[i1, j1] - arr2[i,j])*diag + \
                               (arr[i1, j0] + arr[i0, j1] - arr2[i,j])*diag)*0.75

    @njit(parallel=True)
    def tex_laplacian_ani(lap, arr, VF):
        arr2 = arr*2
        nx = arr.shape[0]
        ny = arr.shape[1]
        i0 = np.arange(nx)-1
        i0[0] = 1
        i1 = np.arange(nx)+1
        i1[nx-1] = nx-2
        j0 = np.arange(ny)-1
        j0[0] = 1
        j1 = np.arange(ny)+1
        j1[ny-1] = ny-2
        for i in prange(nx):
            for j in prange(ny):
                lap[i,j] = (arr[i0[i], j] + arr[i1[i], j] - arr2[i,j])*VF[0,i,j] + \
                               (arr[i, j0[j]] + arr[i, j1[j]] - arr2[i,j])*VF[1,i,j] + \
                               (arr[i0[i], j0[j]] + arr[i1[i], j1[j]] - arr2[i,j])*VF[2,i,j] + \
                               (arr[i1[i], j0[j]] + arr[i0[i], j1[j]] - arr2[i,j])*VF[3,i,j]
        #lap[0,:] = lap[1,:]
        #lap[:,0] = lap[:,1]
        #lap[-1,:] = lap[-2,:]
        #lap[:,-1] = lap[:,-2]

    #@cuda.jit(parallel=True)
    @njit(parallel=True)
    def run_tex_rd(A, B, lap_A, lap_B, diff_A, diff_B, f, k, dt, steps, brush):
        for t in range(steps):
            tex_laplacian(lap_A, A)
            tex_laplacian(lap_B, B)
            nx = A.shape[0]
            ny = A.shape[1]
            for i in prange(nx):
                for j in prange(ny):
                    B[i,j] += brush[i,j]
                    ab2 =  A[i,j]*B[i,j]**2
                    A[i,j] += (lap_A[i,j]*diff_A - ab2 + f*(1-A[i,j]))*dt
                    B[i,j] += (lap_B[i,j]*diff_B + ab2 - (k+f)*B[i,j])*dt

    @njit(parallel=True)
    def run_tex_rd_ani(A, B, lap_A, lap_B, diff_A, diff_B, f, k, dt, steps, vf1, vf2, brush):
        for t in range(steps):
            tex_laplacian_ani(lap_A, A, vf2)
            #laplacian(lap_A, A)
            tex_laplacian_ani(lap_B, B, vf1)
            nx = A.shape[0]
            ny = A.shape[1]
            for i in prange(nx):
                for j in prange(ny):
                    B[i,j] += brush[i,j]
                    ab2 =  A[i ,j]*B[i,j]**2
                    A[i,j] += (lap_A[i,j]*diff_A[i,j] - ab2 + f[i,j]*(1-A[i,j]))*dt
                    B[i,j] += (lap_B[i,j]*diff_B[i,j] + ab2 - (k[i,j]+f[i,j])*B[i,j])*dt


    @njit(parallel=True)
    def numba_reaction_diffusion(n_verts, n_edges, edge_verts, a, b, brush, diff_a, diff_b, f, k, dt, time_steps):
        arr = np.arange(n_edges)
        id0 = edge_verts[arr*2]
        id1 = edge_verts[arr*2+1]
        for i in range(time_steps):
            lap_a, lap_b = rd_init_laplacian(n_verts)
            numba_rd_laplacian(id0, id1, a, b, lap_a, lap_b)
            numba_rd_core(a, b, lap_a, lap_b, diff_a, diff_b, f, k, dt)
            numba_set_ab(a,b,brush)
        return a,b

    @njit(parallel=False)
    def integrate_field(n_edges, id0, id1, values, edge_flow, mult, time_steps):
        #n_edges = len(edge_flow)
        for i in range(time_steps):
            values0 = values
            for j in range(n_edges):
                v0 = id0[j]
                v1 = id1[j]
                values[v0] -= values0[v1] * edge_flow[j] * 0.001#mult[v1]
                values[v1] += values0[v0] * edge_flow[j] * 0.001#mult[v0]
            for j in range(n_edges):
                v0 = id0[j]
                v1 = id1[j]
                values[v0] = max(values[v0],0)
                values[v1] = max(values[v1],0)
        return values

    @njit(parallel=True)
    def numba_reaction_diffusion_anisotropic(n_verts, n_edges, edge_verts, a, b, brush, diff_a, diff_b, f, k, dt, time_steps, field_mult):
        arr = np.arange(n_edges)
        id0 = edge_verts[arr*2]
        id1 = edge_verts[arr*2+1]
        mult = field_mult[arr]
        for i in range(time_steps):
            lap_a, lap_b = rd_init_laplacian(n_verts)
            numba_rd_laplacian_anisotropic(id0, id1, a, b, lap_a, lap_b, mult)
            numba_rd_core(a, b, lap_a, lap_b, diff_a, diff_b, f, k, dt)
            numba_set_ab(a,b,brush)
        return a,b

    #@guvectorize(['(float64[:] ,float64[:] , float64[:], float64[:], float64[:], float64[:], float64[:], float64[:], float64)'],'(n),(n),(n),(n),(n),(n),(n),(n),()',target='parallel')
    @njit(parallel=True)
    def numba_rd_core(a, b, lap_a, lap_b, diff_a, diff_b, f, k, dt):
        n = len(a)
        _f = np.full(n, f[0]) if len(f) == 1 else f
        _k = np.full(n, k[0]) if len(k) == 1 else k
        _diff_a = np.full(n, diff_a[0]) if len(diff_a) == 1 else diff_a
        _diff_b = np.full(n, diff_b[0]) if len(diff_b) == 1 else diff_b

        for i in prange(n):
            fi = _f[i]
            ki = _k[i]
            diff_ai = _diff_a[i]
            diff_bi = _diff_b[i]
            ab2 = a[i]*b[i]**2
            a[i] += (diff_ai * lap_a[i] - ab2 + fi*(1-a[i]))*dt
            b[i] += (diff_bi * lap_b[i] + ab2 - (ki+fi)*b[i])*dt


    @njit(parallel=True)
    def numba_set_ab(a, b, brush):
        n = len(a)
        _brush = np.full(n, brush[0]) if len(brush) == 1 else brush
        for i in prange(len(b)):
            b[i] += _brush[i]
            if b[i] < 0: b[i] = 0
            elif b[i] > 1: b[i] = 1
            if a[i] < 0: a[i] = 0
            elif a[i] > 1: a[i] = 1

    @njit(parallel=True)
    def numba_rd_laplacian(id0, id1, a, b, lap_a, lap_b):
        for i in prange(len(id0)):
            v0 = id0[i]
            v1 = id1[i]
            lap_a[v0] += (a[v1] - a[v0])
            lap_a[v1] += (a[v0] - a[v1])
            lap_b[v0] += (b[v1] - b[v0])
            lap_b[v1] += (b[v0] - b[v1])
        #return lap_a, lap_b

    @njit(parallel=True)
    def numba_rd_laplacian_anisotropic(id0, id1, a, b, lap_a, lap_b, mult):
        for i in prange(len(id0)):
            v0 = id0[i]
            v1 = id1[i]
            multiplier = mult[i]
            lap_a[v0] += (a[v1] - a[v0])# * multiplier
            lap_a[v1] += (a[v0] - a[v1])# * multiplier
            lap_b[v0] += (b[v1] - b[v0]) * multiplier
            lap_b[v1] += (b[v0] - b[v1]) * multiplier
        #return lap_a, lap_b


        #return lap_a, lap_b


    @njit(parallel=True)
    def rd_init_laplacian(n_verts):
        lap_a = np.zeros(n_verts)
        lap_b = np.zeros(n_verts)
        return lap_a, lap_b


    @njit(parallel=True)
    def numba_calc_thickness_area_weight(co2,n2,vz,a,weight):
        shape = co2.shape
        n_patches = shape[0]
        n_verts = shape[1]
        n_co = shape[2]
        nn = n2.shape[1]-1
        na = a.shape[1]-1
        nw = weight.shape[1]-1
        co3 = np.zeros((n_patches,n_verts,n_co))
        for i in prange(n_patches):
            for j in prange(n_verts):
                for k in prange(n_co):
                    co3[i,j,k] = co2[i,j,k] + n2[i,min(j,nn),k] * vz[0,j,0] * a[i,min(j,na),0] * weight[i,min(j,nw),0]
        return co3


    @njit(parallel=True)
    def numba_interp_points(v00, v10, v01, v11, vx, vy):
        n_patches = v00.shape[0]
        n_verts = vx.shape[1]
        n_verts0 = v00.shape[1]
        n_co = v00.shape[2]
        vxy = np.zeros((n_patches,n_verts,n_co))
        for i in prange(n_patches):
            for j in prange(n_verts):
                j0 = min(j,n_verts0-1)
                for k in prange(n_co):
                    co0 = v00[i,j0,k] + (v10[i,j0,k] - v00[i,j0,k]) * vx[0,j,0]
                    co1 = v01[i,j0,k] + (v11[i,j0,k] - v01[i,j0,k]) * vx[0,j,0]
                    vxy[i,j,k] = co0 + (co1 - co0) * vy[0,j,0]
        return vxy

    @njit(parallel=True)
    def numba_interp_points_sk(v00, v10, v01, v11, vx, vy):
        n_patches = v00.shape[0]
        n_sk = v00.shape[1]
        n_verts = v00.shape[2]
        n_co = v00.shape[3]
        vxy = np.zeros((n_patches,n_sk,n_verts,n_co))
        for i in prange(n_patches):
            for sk in prange(n_sk):
                for j in prange(n_verts):
                    for k in prange(n_co):
                        co0 = v00[i,sk,j,k] + (v10[i,sk,j,k] - v00[i,sk,j,k]) * vx[0,sk,j,0]
                        co1 = v01[i,sk,j,k] + (v11[i,sk,j,k] - v01[i,sk,j,k]) * vx[0,sk,j,0]
                        vxy[i,sk,j,k] = co0 + (co1 - co0) * vy[0,sk,j,0]
        return vxy

    @njit
    def numba_lerp(v0, v1, x):
        return v0 + (v1 - v0) * x

    @njit
    def numba_lerp2(v00, v10, v01, v11, vx, vy):
        co0 = numba_lerp(v00, v10, vx)
        co1 = numba_lerp(v01, v11, vx)
        co2 = numba_lerp(co0, co1, vy)
        return co2


#except:
#    print("Tissue: Numba cannot be installed. Try to restart Blender.")
#    pass
