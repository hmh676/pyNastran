from struct import pack, Struct

def write_geom1(op2, op2_ascii, obj):
    #if not hasattr(obj, 'nodes'):
        #return
    if not hasattr(obj, 'nodes'):
        return
    nnodes = len(obj.nodes)
    ncoords = len(obj.coords)
    if not(nnodes or ncoords):
        return
    data = [
        4, 2, 4,
        #4, 2,4,
        8, b'GEOM1   ', 8,
        4, -1, 4,
        #4, 1, 4,
        #4, 0, 4,
    ]
    op2.write(pack('4i 8s i 3i', *data))
    op2_ascii.write(str(data) + '\n')

    data = [
        4, 7, 4,
        28, 1, 2, 3, 4, 5, 6, 7, 28,
    ]
    op2.write(pack('3i 9i', *data))
    op2_ascii.write(str(data) + '\n')

    #-------------------------------------
    data = [
        4, -2, 4,
        4, 1, 4,
        4, 0, 4]
    op2.write(pack('9i', *data))
    op2_ascii.write(str(data) + '\n')

    data = [
        #4, 0, 4,
        4, 2, 4,
        8, 1, 2, 8,
    ]
    op2.write(pack('3i 4i', *data))
    op2_ascii.write(str(data) + '\n')
    #data = [8, 1, 2, 8]
    #op2.write(pack('4i', *data))
    #-------------------------------------

    data = [
        4, -3, 4,
        4, 1, 4,
        4, 0, 4]
    op2.write(pack('9i', *data))
    op2_ascii.write(str(data) + '\n')
    itable = -3

    if nnodes:
        #nvalues = nnodes * 8
        #nbytes = nvalues * 4
        bytes_per_id = 32
        assert nnodes == 72, nnodes
        nfields = 8 # nid, cp, x, y, z, cd, ps, seid
        nvalues = nfields * nnodes + 3 # 3 comes from the keys
        nbytes = nvalues * 4
        assert nbytes == 2316, nbytes
        #op2.write(pack('6i', *[4, 0, 4, 4, 1, 4]))
        op2.write(pack('3i', *[4, nvalues, 4]))
        op2.write(pack('i', nbytes)) #values, nbtyes))

        #op2.write(pack('3i', *[4, 0, 4]))
        #op2_ascii.write(str([4, 0, 4])) #values, nbtyes))

        #(4501,  45,  1): ['GRID',   self._read_grid],
        key = (4501, 45, 1)
        op2.write(pack('3i', *key))
        op2_ascii.write(str(key) + '\n')

        spack = Struct('ii 3f 3i')
        for nid, node in sorted(obj.nodes.items()):
            xyz = node.xyz
            ps = node.ps
            if ps == '':
                psi = 0
            else:
                psi = int(ps)

            seid = node.seid
            if seid == '':
                seidi = 0
            else:
                seidi = int(seid)
            nid = node.nid
            data = [node.nid, node.Cp(), xyz[0], xyz[1], xyz[2], node.Cd(), psi, seidi]
            op2.write(spack.pack(*data))
            op2_ascii.write('  nid=%s cp=%s xyz=(%s, %s, %s) cd=%s ps=%s seid=%s\n' % tuple(data))
        op2.write(pack('i', nbytes))
        itable -= 1

        #-------------------------------------
        itable = -4
        close_geom_table(op2, op2_ascii, itable)

        #-------------------------------------

    if ncoords:
        #(1701,  17,  6): ['CORD1C', self._read_cord1c],
        #(1801,  18,  5): ['CORD1R', self._read_cord1r],
        #(1901,  19,  7): ['CORD1S', self._read_cord1s],
        #(2001,  20,  9): ['CORD2C', self._read_cord2c],
        #(2101,  21,  8): ['CORD2R', self._read_cord2r],
        #(2201,  22, 10): ['CORD2S', self._read_cord2s],
        #(14301,143,651): ['CORD3G', self._read_cord3g],
        pass
    #_write_markers(op2, op2_ascii, [2, 4])

def init_table(table_name):
    data = [
        4, 2, 4,
        #4, 2,4,
        8, b'%8s' % table_name, 8,
        4, -1, 4,
        #4, 1, 4,
        #4, 0, 4,
    ]
    return data

def close_geom_table(op2, op2_ascii, itable):
    data = [
        4, -4, 4,
        4, 1, 4,
        4, 0, 4]
    op2.write(pack('9i', *data))
    op2_ascii.write(str(data) + '\n')

    data = [
        4, 3, 4,
        12, 1, 2, 3, 12]
    op2.write(pack('3i 5i', *data))
    op2_ascii.write(str(data) + '\n')
    #-------------------------------------

    data = [
        4, -5, 4,
        4, 1, 4,
        4, 0, 4]
    op2.write(pack('9i', *data))
    op2_ascii.write(str(data) + '\n')

    data = [
        4, 0, 4,
        #4, 2, 4
    ]
    op2.write(pack('3i', *data))
    op2_ascii.write(str(data) + '\n')
