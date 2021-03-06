"""Defines various helper functions for loading a HDF5 BDF file"""
from __future__ import (nested_scopes, generators, division, absolute_import,
                        print_function, unicode_literals)
from collections import defaultdict
from itertools import count
from six import StringIO, text_type, binary_type
import numpy as np
import h5py

from pyNastran.utils.dict_to_h5py import (
    _add_list_tuple, _cast, integer_types, float_types, string_types)
from pyNastran.bdf.bdf_interface.add_card import CARD_MAP
from pyNastran.bdf.case_control_deck import CaseControlDeck
from pyNastran.utils import object_attributes


# dict[key] : [value1, value2, ...]
dict_int_list_obj_attrs = [
    'spcs', 'spcadds',
    'mpcs', 'mpcadds',
    'loads', 'load_combinations',
    'dloads', 'dload_entries',
    #'usets', # has string keys
    'nsms', 'nsmadds',
    'frequencies',
    'bcs', 'transfer_functions',
    'dvgrids',
]

# dict[key] : value
dict_int_obj_attrs = [
    # are handled explictly----
    #'elements',
    #'nodes',
    #'coords',
    #'materials',
    #'properties',
    #'masses',
    #'tables',
    #'methods',
    #'creep_materials', 'csschds',
    #'flutters',
    #'gusts',
    #'trims',
    #'plotels',
    'MATS1', 'MATS3', 'MATS8', 'MATT1', 'MATT2', 'MATT3', 'MATT4', 'MATT5', 'MATT8', 'MATT9',

    # TODO: don't work
    #'reject_count',
    'dresps',

    'aecomps', 'aefacts', 'aelists', 'aeparams',
    'aestats', 'aesurf', 'aesurfs', 'ao_element_flags', 'bconp', 'bcrparas', 'bctadds',
    'bctparas', 'bctsets', 'blseg', 'bsurf', 'bsurfs', 'cMethods',
    'convection_properties',
    'csuper', 'csupext', 'dareas',
    'dconadds', 'ddvals', 'delays', 'dequations', 'divergs', 'dlinks',
    'dmigs', 'dmijis', 'dmijs', 'dmiks', 'dmis',
    'dphases',
    'dscreen', 'dti', 'dvcrels', 'dvmrels', 'dvprels',
    'epoints', 'flfacts',
    'gridb',
    'nlparms', 'nlpcis',
    'normals',
    'nxstrats', 'paeros',
    'pbusht', 'pdampt', 'pelast', 'phbdys', 'points',
    'properties_mass',
    'radcavs', 'radmtx', 'random_tables',
    'ringaxs', 'ringfl',
    'rotors',
    'se_sets', 'se_usets', 'sebndry', 'sebulk', 'seconct', 'seelt',
    'seexcld', 'selabel', 'seload', 'seloc', 'sempln', 'senqset', 'setree', 'sets',
    'spcoffs',
    'spoints',
    'suport1',
    'tables_d', 'tables_m', 'tables_sdamping', 'tempds',
    'tics',
    'tstepnls', 'tsteps',
    'view3ds', 'views',
]

scalar_obj_keys = [
    # required----
    'aero', 'aeros', 'axic', 'axif', 'baror', 'beamor',
    'doptprm',
    'dtable', 'grdset', 'radset', 'seqgp',
    'case_control_deck',
    #'zona',
]

scalar_keys = [
    # handled separately----
    #'cards_to_read',

    # basic types----
    'bdf_filename',
    '_auto_reject', '_encoding', '_iparse_errors', '_is_axis_symmetric', '_is_cards_dict',
    '_is_dynamic_syntax', '_is_long_ids', '_ixref_errors', '_nastran_format', '_nparse_errors',
    '_nxref_errors', '_sol', '_stop_on_duplicate_error', '_stop_on_parsing_error',
    '_stop_on_xref_error',
    '_xref', 'active_filename',
    'dumplines', 'echo', 'force_echo_off', 'include_dir',
    'is_msc', 'is_nx', 'punch',
    'read_includes', 'save_file_structure', 'sol', 'sol_iline', 'nastran_format',
    'is_superelements', 'is_zona', 'sol_method', 'debug',
    #'_unique_bulk_data_cards',
    #'is_bdf_vectorized',
    #'is_long_ids',


    # not sure----
    #'nid_cp_cd', 'xyz_cid0',

    # removed-----
    #'ncaeros', 'ncoords', 'nnodes', 'nelements', 'nproperties', 'nmaterials',
    #'point_ids', 'wtmass', 'log',
]

LIST_KEYS = [
    # handled in minor_attributes----
    #'active_filenames', 'executive_control_lines', 'case_control_lines',
    #'system_command_lines',
    #'reject_cards',

    # required------------------
    #'initial_superelement_models',

    # maybe...
    #'_duplicate_coords', '_duplicate_elements', '_duplicate_masses', '_duplicate_materials',
    '_duplicate_nodes', '_duplicate_properties',
    '_duplicate_thermal_materials', '_stored_parse_errors',
    #'_stored_xref_errors',
    #'units', 'xyz_limits',

    # removed
    #'coord_ids', 'element_ids', 'material_ids', 'node_ids', 'property_ids', 'caero_ids',
    #'special_cards',
]

LIST_OBJ_KEYS = [  ## TODO: not done
    # TODO: required
    'asets', 'bsets', 'csets', 'omits', 'qsets',
    'mkaeros',
    'monitor_points',
    'suport',
    'se_bsets', 'se_csets', 'se_qsets', 'se_suport',
]

dict_attrs = [
    # required
    'params',

    # removed
    #'_solmap_to_value',
    #'card_count',
    #'_card_parser',
    #'_card_parser_prepare',
    #'_slot_to_type_map',
    #'_type_to_id_map',
    #'_type_to_slot_map',
]

def export_to_hdf5_file(hdf5_file, model, exporter=None):
    """
    Converts the BDF objects into hdf5 object

    Parameters
    ----------
    hdf5_file : H5File()
        an h5py object
    exporter : HDF5Exporter; default=None
        unused

    """
    attrs = object_attributes(model, mode='both', keys_to_skip=None)
    encoding = model.get_encoding()

    if 'GRID' in model.card_count:
        model.log.debug('exporting nodes')
        node_group = hdf5_file.create_group('nodes')
        grid_group = node_group.create_group('GRID')
        nids = model._type_to_id_map['GRID']
        if len(nids) == 0:
            assert len(model.nodes) == 0, len(model.nodes)
        CARD_MAP['GRID'].export_to_hdf5(grid_group, model, nids)

    _hdf5_export_group(hdf5_file, model, 'coords', encoding, debug=False)
    _hdf5_export_elements(hdf5_file, model, encoding)

    # explicit groups
    #
    # these are broken down by card type
    # they came from dict_int_obj_attrs
    groups_to_export = [
        'properties', 'masses', 'rigid_elements', 'plotels',

        # materials
        'materials', 'thermal_materials', 'creep_materials', 'hyperelastic_materials',
        #'MATS1',
        #'MATT1', 'MATT2', 'MATT3', 'MATT4', 'MATT5', 'MATT8', 'MATT9',

        # aero
        'caeros', 'splines', 'flutters', 'trims', 'csschds', 'gusts',

        # other
        'methods', 'tables', 'desvars',
    ]
    for group_name in groups_to_export:
        _hdf5_export_group(hdf5_file, model, group_name, encoding)


    dict_int_attrs = [  # TODO: not used...
        # required
        '_dmig_temp',
        'include_filenames',
        'superelement_models',
        'values_to_skip',

        # removed
        #'rsolmap_to_str',
        #'nid_map',
        #'subcases',
    ]

    _export_dict_int_obj_attrs(model, hdf5_file, encoding)
    _export_dict_int_list_obj_attrs(model, hdf5_file, encoding)
    _export_dconstrs(hdf5_file, model, encoding)

    #for key in scalar_obj_keys:
        #value = getattr(model, key)
        #hdf5_file.create_dataset(key, value)
    if model.params:
        model.log.debug('exporting params')
        skip_attrs = ['comment', '_field_map']
        group = hdf5_file.create_group('params')
        for key, param in model.params.items():
            _h5_export_class(group, model, key, param, skip_attrs, encoding, debug=False)

    if model.aelinks:
        model.log.debug('exporting aelinks')
        skip_attrs = ['comment', '_field_map']
        group = hdf5_file.create_group('aelinks')
        for aelink_id, aelinks in model.aelinks.items():
            groupi = group.create_group(str(aelink_id))
            for j, aelinki in enumerate(aelinks):
                key = str(j)
                _h5_export_class(groupi, model, key, aelinki, skip_attrs, encoding, debug=False)

    if model.usets:
        model.log.debug('exporting usets')
        skip_attrs = ['comment', '_field_map']
        group = hdf5_file.create_group('usets')
        for name, usets in model.usets.items():
            groupi = group.create_group(name)
            print(usets)
            for i, uset in enumerate(usets):
                print(uset.get_stats())
                key = str(i)
                _h5_export_class(groupi, model, key, uset, skip_attrs, encoding, debug=False)

    _export_scalar_group(hdf5_file, model, encoding)

    skip_attrs = ['comment', '_field_map']
    for key in scalar_obj_keys:
        value = getattr(model, key)
        if value is None:
            #print('None: %s %s' % (key, value))
            pass
        else:
            model.log.debug('exporting %s' % key)
            _h5_export_class(hdf5_file, model, key, value, skip_attrs, encoding, debug=False)

    _export_list_keys(model, hdf5_file, LIST_KEYS)
    _export_list_obj_keys(model, hdf5_file, LIST_OBJ_KEYS, encoding)

    cards_to_read = [key.encode(encoding) for key in list(model.cards_to_read)]
    cards_to_read = list(cards_to_read)
    cards_to_read.sort()
    hdf5_file.create_dataset('cards_to_read', data=cards_to_read)
    #dict_keys2 = []
    #list_keys2 = []
    #other_keys2 = []
    #for key in attrs:
        #value = getattr(model, key)
        #if isinstance(value, dict):
            #dict_keys2.append(key)
        #elif isinstance(value, list):
            #list_keys2.append(key)
        #else:
            #other_keys2.append(key)

    #print('dict_keys2 = %s' % (set(dict_keys) - set(dict_keys2)))
    #print('list_keys2 = %s' % (set(list_keys) - set(list_keys2)))
    #print('other_keys2 = %s' % (set(other_keys) - set(other_keys2)))
    #asd


def _export_dconstrs(hdf5_file, model, encoding):
    """exports the dconstrs, which includes DCONSTRs and DCONADDs"""
    if model.dconstrs:
        dconstrs_group = hdf5_file.create_group('dconstrs')
        keys = list(model.dconstrs.keys())

        dconstrsi = []
        dconadds = []
        for key, dconstrs in model.dconstrs.items():
            #group = dconstrs_group.create_group(str(key))
            for dconstr in dconstrs:
                Type = dconstr.type
                if Type == 'DCONSTR':
                    dconstrsi.append(dconstr)
                elif Type == 'DCONADD':
                    dconadds.append(dconstr)

        ndconstrs = len(dconstrsi)
        if ndconstrs:
            dconstr_group = dconstrs_group.create_group('DCONSTR')
            keys = np.arange(ndconstrs, dtype='int32')
            dconstr0 = dconstrsi[0]
            dconstr0.export_to_hdf5(dconstr_group, dconstrsi, encoding)
            ndconstrs = len(dconstrsi)

        ndconadds = len(dconadds)
        if ndconadds:
            dconadd_group = dconstrs_group.create_group('DCONADD')
            keys = np.arange(ndconadds, dtype='int32')
            dconadds0 = dconadds[0]
            dconadds0.export_to_hdf5(dconadd_group, dconadds, encoding)

def _export_scalar_group(hdf5_file, model, encoding):
    scalar_group = _export_minor_attributes(hdf5_file, model, encoding)

    for key in ['case_control_lines', 'executive_control_lines',
                'system_command_lines', 'active_filenames']:
        # these are exported to the minor_attributes group
        list_str = getattr(model, key)
        if not len(list_str):
            continue
        list_bytes = [line.encode(encoding) for line in list_str]
        #print(scalar_group)
        scalar_group.create_dataset(key, data=list_bytes)

    if len(model.reject_lines):
        reject_group = scalar_group.create_group('reject_lines')
        for i, list_str in enumerate(model.reject_lines):
            list_bytes = [line.encode(encoding) for line in list_str]
            reject_group.create_dataset(str(i), data=list_bytes)

    if len(model.reject_cards):
        reject_group = scalar_group.create_group('reject_cards')
        for i, reject_card in enumerate(model.reject_cards):
            fields = reject_card.fields()
            list_bytes = [field.encode(encoding) if field is not None else b''
                          for field in fields]
            reject_group.create_dataset(str(i), data=list_bytes)

def _export_minor_attributes(hdf5_file, model, encoding):
    scalar_group = None
    scalars_keys_to_analyze = []
    for key in scalar_keys:
        if hasattr(model, key):
            scalars_keys_to_analyze.append(key)

    if scalars_keys_to_analyze:
        scalar_group = hdf5_file.create_group('minor_attributes')
        scalar_group.create_dataset('encoding', data=encoding)
        for key in sorted(scalars_keys_to_analyze):
            value = getattr(model, key)
            #model.log.debug('  minor %s' % key)

            if value is None:
                continue
                #print('None: %s %s' % (key, value))

            #elif isinstance(value, bool):
                #print('bool: %s %s' % (key, value))
            elif isinstance(value, (integer_types, float_types, string_types, np.ndarray)):
                try:
                    scalar_group.create_dataset(key, data=value)
                except TypeError:  # pragma: no cover
                    print('key=%r value=%s type=%s' % (key, str(value), type(value)))
                    raise
            #elif isinstance(value, set):
                #_add_list_tuple(hdf5_file, key, value, 'set', model.log)
            elif isinstance(value, StringIO):
                pass
            else:
                #print(key, value)
                scalar_group.create_dataset(key, data=value)
        #del scalar_group

    scalar_group.create_dataset('is_enddata', data='ENDDATA' in model.card_count)
    return scalar_group

def _export_dict_int_obj_attrs(model, hdf5_file, encoding):
    cards = set(list(CARD_MAP.keys()))
    for attr in dict_int_obj_attrs:
        dict_obj = getattr(model, attr)
        #print(attr, dict_obj)
        if not len(dict_obj):
            continue

        #model.log.info(attr)
        try:
            group = hdf5_file.create_group(attr) # 'gusts'
        except ValueError:  # pragma: no cover
            model.log.error('cant create %r' % attr)
            raise
        _hdf5_export_object_dict(group, model, attr, dict_obj, dict_obj.keys(), encoding)

def _export_dict_int_list_obj_attrs(model, hdf5_file, encoding):
    for attr in dict_int_list_obj_attrs:
        dict_obj = getattr(model, attr) # spcs
        if not len(dict_obj):
            continue

        model.log.debug('exporting %s' % attr)
        try:
            group = hdf5_file.create_group(attr) # 'spcs'
        except ValueError:  # pragma: no cover
            model.log.error('cant create %r' % attr)
            raise

        keys = list(dict_obj.keys())
        keys.sort()
        #model.log.debug('keys = %s' % keys)
        if attr in ['dmigs', 'dmijs', 'dmis', 'dmiks', 'dmijis']:
            #print('keys =', keys)
            key0 = keys[0]
            value = dict_obj[key0]
            group.attrs['type'] = value.type
            #print('setting type', group, value.type)
            model.log.debug('type = %s' % value.type)
            model.log.debug('export 364')
            value.export_to_hdf5(group, model, encoding)
            return

        group.create_dataset('keys', data=keys)
        for spc_id, spcs_obj in sorted(dict_obj.items()):
            id_group = group.create_group(str(spc_id))

            card_types = defaultdict(list)
            for spc in spcs_obj:
                card_types[spc.type].append(spc)
            for card_type, spcs in card_types.items():
                card_group = id_group.create_group(card_type)

                class_obj = spcs[0]
                if hasattr(class_obj, 'export_to_hdf5'):
                    class_obj.export_to_hdf5(card_group, model, spcs)
                else:
                    indices = list(range(len(spcs)))
                    _hdf5_export_object_dict(card_group, model,
                                             '%s/id=%s/%s' % (attr, spc_id, card_type),
                                             spcs, indices, encoding)

def _export_list_keys(model, hdf5_file, list_keys):
    for attr in list_keys:
        #print('list_key: %s' % attr)
        list_obj = getattr(model, attr) # active_filenames
        if not len(list_obj):
            continue
        #model.log.info(attr)

        #try:
            #group = hdf5_file.create_group(attr) # 'active_filenames'
        #except ValueError:
            #model.log.error('cant create %r' % attr)
            #raise

        if isinstance(list_obj, list):
            Type = 'list'
        elif isinstance(list_obj, tuple):
            Type = 'tuple'
        else:
            raise NotImplementedError(type(list_obj))
        #indices = list(range(len(list_keys)))
        #group.create_dataset('keys', data=keys)

        if isinstance(list_obj[0], (int, float, string_types)):
            try:
                _add_list_tuple(hdf5_file, attr, list_obj, Type, model.log)
            except TypeError:  # pragma: no cover
                print(list_obj)
                raise
        #elif isinstance(list_obj[0], list):
            #group = hdf5_file.create_group(attr)
            #group.attrs['type'] = Type
            #for keyi, valuei in enumerate(list_obj):
                ##sub_group = hdf5_file.create_group(str(keyi))
                ##group
                #_add_list_tuple(group, str(keyi), valuei, Type, model.log)
        else:
            raise NotImplementedError(type(list_obj[0]))
        #_hdf5_export_object_dict(group, model, attr, list_obj, indices, encoding)


def _export_list_obj_keys(model, hdf5_file, list_obj_keys, encoding):
    for attr in list_obj_keys:
        list_obj = getattr(model, attr) # active_filenames
        if not len(list_obj):
            #model.log.debug('skipping list_key: %s' % attr)
            continue
        model.log.debug('exporting %s' % attr)

        try:
            group = hdf5_file.create_group(attr) # 'active_filenames'
        except ValueError:  # pragma: no cover
            model.log.error('cant create %r' % attr)
            raise

        #if isinstance(list_obj, list):
            #Type = 'list'
        #elif isinstance(list_obj, tuple):
            #Type = 'tuple'
        #else:
            #raise NotImplementedError(type(list_obj))

        indices = list(range(len(list_obj)))
        #group.create_dataset('keys', data=indices)
        #try:
            #_add_list_tuple(hdf5_file, attr, list_obj, Type, model.log)
        #except TypeError:
            #print(list_obj)
            #raise
        _hdf5_export_object_dict(group, model, attr, list_obj, indices, encoding)


def _h5_export_class(sub_group, model, key, value, skip_attrs, encoding, debug=True):
    #model.log.debug('exporting %s to hdf5' % key)
    #sub_groupi = sub_group.create_group('values')
    class_group = sub_group.create_group(str(key))
    try:
        class_group.attrs['type'] = value.type
    except:  # pragma: no cover
        print('key = %r' % key)
        print('value', value)
        model.log.error('ERROR: key=%s value=%s' % (key, value))
        raise

    #if hasattr(value, 'get_h5attrs'):
        #getattrs

    if hasattr(value, 'export_to_hdf5'):
        #print('value =', value, type(value))
        #print('class_group', class_group)
        #model.log.debug('  export 477 - %s' % class_group)
        value.export_to_hdf5(class_group, model, encoding)
        return
    elif hasattr(value, 'object_attributes'):
        keys_to_skip = []
        if hasattr(value, '_properties'):
            keys_to_skip = value._properties
        h5attrs = value.object_attributes(mode='both', keys_to_skip=keys_to_skip)
        if hasattr(value, '_properties'):
            h5attrs.remove('_properties')
        #sub_group = hdf5_file.create_group(key)
    else:
        raise NotImplementedError(value)

    #if hasattr(value, '_properties'):
        #print(value.type, value._properties)
        #if debug:
            #print(h5attrs)
        #for prop in value._properties:
            #try:
                #h5attrs.remove(prop)
            #except:
                #print('cant remove %s' % prop)
                #print(value)
                #raise
        #h5attrs.remove('_properties')

    if debug:
        model.log.debug(value)

    for h5attr in h5attrs:
        if '_ref' in h5attr or h5attr in skip_attrs:
            continue
        class_value = getattr(value, h5attr)
        if class_value is None:
            continue

        #model.log.info('%s %s %s' % (key, h5attr, class_value))
        if debug:
            model.log.info('%s %s %s' % (key, h5attr, class_value))

        if isinstance(class_value, dict):
            class_group.attrs['type'] = 'dict'
            param_group = class_group.create_group(h5attr)
            keysi = []
            valuesi = []
            for i, (keyi, valuei) in enumerate(class_value.items()):
                keysi.append(keyi)
                valuesi.append(valuei)
                #if isinstance(valuei, text_type):
                    #param_group.create_dataset(str(i), data=valuei.encode('ascii'))
                #elif valuei is None:
                    #param_group.create_dataset(str(i), data=np.nan)
                #else:
                    #param_group.create_dataset(str(i), data=valuei)
            model.log.debug('loading dict as keys/values for %s' % h5attr)
            _export_list(param_group, '%s/%s/%s' % (value.type, key, h5attr), 'keys', keysi, encoding)
            _export_list(param_group, '%s/%s/%s' % (value.type, key, h5attr), 'values', valuesi, encoding)
            continue
        elif isinstance(class_value, (list, np.ndarray)):
            if len(class_value) == 0: # empty list
                continue

            is_nones = []
            for class_valuei in class_value:
                is_none = False
                if class_valuei is None:  # PAERO2 : lth
                    is_none = True
                    #break
                is_nones.append(is_none)
        elif isinstance(class_value, (integer_types, float_types, string_types, bool)):
            is_nones = [False]
        #elif isinstance(class_value, dict) and len(class_value) == 0:
            #pass
        else:
            raise NotImplementedError('%s %s; class_value=%s type=%s' % (
                getattr(value, 'type'), key, class_value, type(class_value)))

        is_none = any(is_nones)

        if all(is_nones):
            model.log.warning('skipping %s attribute: %s %s %s' % (
                value.type, key, h5attr, class_value))
        elif all([not is_nonei for is_nonei in is_nones]): # no Nones
            # no Nones
            try:
                class_group.create_dataset(h5attr, data=class_value)
            except ValueError:  # pragma: no cover
                print(h5attr, class_group)
                raise
            except TypeError:
                # contains unicode
                class_group.attrs['type'] = 'list'
                param_group = class_group.create_group(h5attr)
                for i, valuei in enumerate(class_value):
                    if isinstance(valuei, text_type):
                        param_group.create_dataset(str(i), data=valuei.encode('ascii'))
                    else:
                        param_group.create_dataset(str(i), data=valuei)
                #if isinstance(class_value, list):
                    #print('type(value[0] =', class_value, type(class_value[0]))
                    #raise
        else:
            # mixed Nones and values
            class_group.attrs['type'] = 'list'
            param_group = class_group.create_group(h5attr)
            for i, valuei in enumerate(class_value):
                if isinstance(valuei, text_type):
                    param_group.create_dataset(str(i), data=valuei.encode('ascii'))
                elif valuei is None:
                    param_group.create_dataset(str(i), data=np.nan)
                else:
                    param_group.create_dataset(str(i), data=valuei)

            #raise RuntimeError('mixed %s attribute: %s %s %s' % (
                #value.type, key, h5attr, class_value))

    #assert isinstance(key, int), 'key=%s value=%s' % (key, value)

    if isinstance(value, list):
        raise NotImplementedError('list: %s' % value)
        #for valuei in value:
            #if valuei.type not in cards:
                #msg = 'key=%s type=%s value=%s=' % (key, valuei.type, value)
                #print(msg)
        #continue

    #if attr in ['elements']:
        #continue
    #if value.type not in cards:
        #msg = 'key=%s type=%s value=%s=' % (key, value.type, value)
        #print(msg)

def _export_list(h5_group, attr, name, values, encoding):
    """
    exports a list of:
     - constant type to a dataset
     - variable type to a numbered list
    """
    values2 = [value.encode(encoding) if isinstance(value, text_type) else value
               for value in values]
    types = {type(value) for value in values}
    if len(types) == 1:
        #print('types =', types)
        if not isinstance(values[0], (integer_types, float_types, string_types)):
            #print(attr, name)
            raise TypeError('not a base type; %s; %s' % (attr, values2))
        try:
            h5_group.create_dataset(name, data=values2)
        except TypeError:  # pragma: no cover
            print(attr, name, values2)
            raise
    else:
        sub_group = h5_group.create_group(name)
        sub_group.attrs['type'] = 'list'
        for i, value in enumerate(values2):
            if value is None:
                sub_group.create_dataset(str(i), data=np.nan)
            else:
                try:
                    sub_group.create_dataset(str(i), data=value)
                except TypeError:  # pragma: no cover
                    print(attr, name, values2, i)
                    raise

        #print('%s2' % name, values2)
        #h5_group.create_dataset(name, data=values2)
        #raise

def _hdf5_export_elements(hdf5_file, model, encoding):
    """
    exports the elements to an hdf5_file

    TODO: not done
    """
    etypes_actual = []
    etypes = model._slot_to_type_map['elements']
    for card_name in model.card_count:
        #CTRIA3, CQUAD4
        #CONROD
        #CBUSH
        #CBEAM
        #CPENTA, CHEXA
        if card_name in etypes:
            #model.log.debug(card_name)
            etypes_actual.append(card_name)
            continue

    if etypes_actual:
        elements_group = hdf5_file.create_group('elements')
        def save_solids(etype, slot_name):
            element_group = elements_group.create_group(etype)
            eids = model._type_to_id_map[etype]
            CARD_MAP[slot_name].export_to_hdf5(element_group, model, eids)

        solids = [
            ('CTETRA', 'CTETRA4'),
            ('CPENTA', 'CPENTA6'),
            ('CPYRAM', 'CPYRAM5'),
            ('CHEXA', 'CHEXA20'),
        ]
        for card_name, slot_name in solids:
            if card_name in model.card_count:
                save_solids(card_name, slot_name)
                etypes_actual.remove(card_name)

        for card_type in etypes_actual:
            element_group = elements_group.create_group(card_type)
            eids = model._type_to_id_map[card_type]
            class_obj = CARD_MAP[card_type]

            if hasattr(class_obj, 'export_to_hdf5'):
                class_obj.export_to_hdf5(element_group, model, eids)
            else:
                _hdf5_export_object_dict(element_group, model, card_type,
                                         model.elements, eids, encoding)

def _hdf5_export_group(hdf5_file, model, group_name, encoding, debug=False):
    """
    exports the properties to an hdf5_file
    """
    data_dict = getattr(model, group_name) # model.properties

    #if group_name in ['splines']:
        #debug = True
    if debug:
        model.log.debug('%s %s' % (group_name, data_dict))

    types_actual = []
    types = model._slot_to_type_map[group_name]
    if debug:
        model.log.debug('card_count = %s' % model.card_count)
        model.log.debug('types = %s' % types)

    for card_name in types:
        #PSHELL
        if card_name in model.card_count:
            types_actual.append(card_name)
            continue

    if types_actual:
        model.log.debug('exporting %s' % group_name)
        if debug:  # pragma: no cover
            print('types_actual =', types_actual)

        group = hdf5_file.create_group(group_name)
        for card_type in types_actual:
            sub_group = group.create_group(card_type)
            ids = model._type_to_id_map[card_type]
            if debug:  # pragma: no cover
                print(ids)
            assert len(ids) > 0, '%s : %s' % (card_type, ids)
            class_obj = CARD_MAP[card_type]
            #print(class_obj)
            if hasattr(class_obj, 'export_to_hdf5'):
                class_obj.export_to_hdf5(sub_group, model, ids)
            else:
                _hdf5_export_object_dict(sub_group, model, card_type, data_dict, ids, encoding)
    #else:
        #model.log.debug('skipping %s to hdf5' % group_name)

def _hdf5_export_object_dict(group, model, name, obj_dict, keys, encoding):
    i = 0
    skip_attrs = ['comment', '_field_map']

    keys_write = list(keys)
    if name in ['dmigs', 'dmijs', 'dmiks', 'dmijis', 'dmis', 'dresps']:
        keys = list(keys)
        #print(group)
        key0 = keys_write[0]
        value = obj_dict[key0]
        group.attrs['type'] = value.type
        #print('group...', group)
        model.log.debug('exporting %s' % name)
        value.export_to_hdf5(group, model, encoding)
        return

    if isinstance(keys_write[0], text_type):
        keys_write = list([key.encode(encoding) if isinstance(key, text_type) else key
                           for key in list(keys_write)])

    sub_group = group.create_group('values')
    assert isinstance(name, string_types), 'name=%s; type=%s' % (name, type(name))

    for key in keys:
        value = obj_dict[key]
        #if isinstance(value, text_type):
            #value = value.encode(encoding)

        try:
            _h5_export_class(sub_group, model, key, value, skip_attrs, encoding, debug=False)
        except:  # pragma: no cover
            raise
            # for debugging
            #sub_group2 = group.create_group('values2')
            #_h5_export_class(sub_group2, model, key, value, skip_attrs, encoding, debug=True)
        i += 1

    #group.attrs['type'] = class_name
    #print('%s keys = %s' % (name, keys))
    try:
        group.create_dataset('keys', data=keys_write)
    except TypeError:  # pragma: no cover
        print('name =', name)
        print('encoding =', encoding)
        print('keys =', keys)
        raise

# exporter
#-------------------------------------------------------------------------------------
# importer
def load_hdf5_file(h5_file, model):
    """
    Loads an h5 file object into an OP2 object

    Parameters
    ----------
    h5_file : H5File()
        an h5py file object
    model : BDF()
        the BDF file to put the data into

    """
    encoding = _cast(h5_file['minor_attributes']['encoding'])
    keys = h5_file.keys()

    mapper = {
        'elements' : hdf5_load_elements,
        'plotels' : hdf5_load_plotels,
        'properties' : hdf5_load_properties,
        'coords' : hdf5_load_coords,
        'tables' : hdf5_load_tables,
        'methods' : hdf5_load_methods,
        'masses' : hdf5_load_masses,
        'materials' : hdf5_load_materials,

        'spcs' : hdf5_load_spcs,
        'spcadds' : hdf5_load_spcadds,
        'mpcs' : hdf5_load_mpcs,
        'mpcadds' : hdf5_load_mpcadds,

        'loads' : hdf5_load_loads,
        'load_combinations' : hdf5_load_load_combinations,
        'dloads' : hdf5_load_dloads,
        'dload_entries' : hdf5_load_dload_entries,
        'bcs' : hdf5_load_bcs,
        'transfer_functions' : hdf5_load_transfer_functions,
        'dvgrids': hdf5_load_dvgrids,

        'nsms' : hdf5_load_nsms,
        'nsmadds' : hdf5_load_nsmadds,
        'frequencies' : hdf5_load_frequencies,
        'aelinks' : hdf5_load_aelinks,
        'desvars' : hdf5_load_desvars,

        'dmigs' : hdf5_load_dmigs,
        'dmijs' : hdf5_load_dmigs,
        'dmiks' : hdf5_load_dmigs,
        'dmijis' : hdf5_load_dmigs,
        'dmis' : hdf5_load_dmigs,

        'dconstrs' : hdf5_load_dconstrs,
        'dresps' : hdf5_load_dresps,
        'usets' : hdf5_load_usets,
    }
    generic_mapper = {
        'rigid_elements' : hdf5_load_generic,
        'thermal_materials' : hdf5_load_generic,
        'creep_materials' : hdf5_load_generic,
        'hyperelastic_materials' : hdf5_load_generic,

        'flutters' : hdf5_load_generic,
        'trims' : hdf5_load_generic,
        'csschds' : hdf5_load_generic,
        'gusts' : hdf5_load_generic,
        'caeros' : hdf5_load_generic,
        'splines' : hdf5_load_generic,
        #'MATS1' : hdf5_load_generic,
        #'MATT1' : hdf5_load_generic,
        #'MATT2' : hdf5_load_generic,
        #'MATT3' : hdf5_load_generic,
        #'MATT4' : hdf5_load_generic,
        #'MATT5' : hdf5_load_generic,
        #'MATT8' : hdf5_load_generic,
        #'MATT9' : hdf5_load_generic,
    }
    #print('keys =', list(keys))
    for key in keys:
        model.log.debug('loading %s' % key)
        group = h5_file[key]
        if key == 'nodes':
            grids = group['GRID']
            nids = _cast(grids['nid'])
            xyz = _cast(grids['xyz'])
            cp = _cast(grids['cp'])
            cd = _cast(grids['cd'])
            ps = _cast(grids['ps'])
            seid = _cast(grids['seid'])
            for nid, xyzi, cpi, cdi, psi, seidi in zip(nids, xyz, cp, cd, ps, seid):
                model.add_grid(nid, xyzi, cp=cpi, cd=cdi, ps=psi, seid=seidi, comment='')
            model.card_count['GRID'] = len(nids)

        elif key in mapper:
            func = mapper[key]
            func(model, group, encoding)
        elif key in generic_mapper:
            func = generic_mapper[key]
            func(model, group, key, encoding)
        elif key in dict_int_obj_attrs:
            #model.log.debug('  dict_int_obj')
            dkeys, values = load_cards_from_keys_values(
                key, group, encoding, model.log, debug=False)
            _put_keys_values_into_dict(model, key, dkeys, values)
            card_type = values[0].type
            model.card_count[card_type] = len(dkeys)

        elif key in ['info', 'matrices'] or key.startswith('Subcase'): # op2
            continue
        elif key in ['cards_to_read']: # handled separaaately
            continue
        elif key == 'params':
            keys = list(group.keys())
            values = _load_cards_from_keys_values('params', group, keys, encoding, model.log)
            _put_keys_values_into_dict(model, 'params', keys, values, cast_int_keys=False)
            model.card_count['PARAM'] = len(keys)

        elif key == 'minor_attributes':
            _load_minor_attributes(key, group, model, encoding)
        #elif key in ['case_control_lines', 'executive_control_lines', 'system_command_lines']:
            #lst = _load_indexed_list_str(keyi, sub_group, encoding)

        elif key == 'active_filenames':
            if 'value' not in group:
                lst = _load_indexed_list_str(key, group, encoding)
                continue

            lst = _cast(group['value']).tolist()
            #else:
            #except KeyError:  # pragma: no cover
                #print('group', group)
                #print('group.keys()', list(group.keys()))
                #raise

            if isinstance(lst[0], text_type):
                pass
            else:
                lst = [line.encode(encoding) for line in lst]
            setattr(model, key, lst)

        elif key in LIST_OBJ_KEYS:
            #model.log.debug('  list_obj')
            #model.log.info('  key = %s' % key)
            #model.log.info('  group = %s' % group)
            #model.log.info('  group.keys() = %s' % list(group.keys()))
            keys = _cast(group['keys'])
            values = group['values']
            lst = [None] * len(keys)
            for keyi in values.keys():
                ikey = int(keyi)
                class_obj_hdf5 = values[keyi]
                card_type = _cast(class_obj_hdf5['type'])
                class_instance = _load_from_class(class_obj_hdf5, card_type, encoding)
                lst[ikey] = class_instance
            _put_keys_values_into_list(model, key, keys, lst)
            #model.log.info('keys = %s' % keys)
            #model.log.info('values = %s' % values)
            #model.log.info('values.keys() = %s' % values.keys())

        elif key in 'case_control_deck':
            lines = []
            model.case_control_deck = CaseControlDeck(lines, log=model.log)
            model.case_control_deck.load_hdf5_file(group, encoding)
            str(model.case_control_deck)

        elif key in scalar_obj_keys: # these only have 1 value
            #model.log.debug('  scalar_obj')
            keys = list(group.keys())
            keys.remove('type')
            card_type = _cast(group['type'])
            class_instance = _load_from_class(group, card_type, encoding)
            write_card(class_instance)
            setattr(model, key, class_instance)
            model.card_count[card_type] = 1
        #elif key in scalar_keys:
            #value = _cast(group)
            #try:
                #setattr(model, key, value)
            #except AttributeError:
                #model.log.warning('cant set %r as %s' % (key, value))
                #raise

        #elif key in list_keys:
            #value = _cast(group)
            #try:
                #setattr(model, key, value)
            #except AttributeError:
                #model.log.warning('cant set %r as %s' % (key, value))
                #raise
        else:
            model.log.warning('skipping hdf5 load for %s' % key)
            raise RuntimeError('skipping hdf5 load for %s' % key)

    cards_to_read = _cast(h5_file['cards_to_read'])
    cards_to_read = [key.decode(encoding) for key in cards_to_read]
    model.cards_to_read = set(list(cards_to_read))

def _load_minor_attributes(key, group, model, encoding):
    keys_attrs = group.keys()
    for keyi in keys_attrs:
        sub_group = group[keyi]
        model.log.debug('  %s' % keyi)

        if keyi in ['case_control_lines', 'executive_control_lines',
                    'system_command_lines', 'active_filenames']:
            lst = _cast(sub_group).tolist()
            if isinstance(lst[0], text_type):
                pass
            else:
                lst = [line.decode(encoding) for line in lst]
                assert isinstance(lst[0], text_type), type(lst[0])
            setattr(model, keyi, lst)
            continue
        elif keyi == 'reject_lines':
            reject_keys = list(sub_group.keys())
            lst = [None] * len(reject_keys)

            for reject_key in reject_keys:
                reject_key_int = int(reject_key)
                h5_value = sub_group[reject_key]
                value = _cast(h5_value).tolist()
                lst[reject_key_int] = value
                comment = value[0].decode(encoding)
                card_lines = value[1:]
                card_lines = [line.decode(encoding) for line in card_lines]
                try:
                    line0 = card_lines[0]
                except IndexError:
                    # C:\Program Files\Siemens\NX 12.0\NXNASTRAN\nxn12\nast\del\gentim1.dat
                    print(value)
                    print(card_lines)
                    raise
                card_name = line0.split(',', 1)[0].split('\t', 1)[0][:8].rstrip().upper().rstrip('*')
                assert isinstance(comment, text_type), type(comment)

                ## TODO: swap out
                #model.add_card(card_lines, card_name, comment=comment,
                               #ifile=None, is_list=True, has_none=True)
                model.reject_card_lines(card_name, card_lines, comment)
            continue
        elif keyi == 'reject_cards':
            reject_keys = list(sub_group.keys())
            for ireject in sub_group.keys():
                reject_card = _cast(sub_group[ireject]).tolist()
                fields = [val.decode(encoding) for val in reject_card]
                #fields = [field if field != 'nan' else None for field in fields]
                card_name = fields[0]
                model.add_card(fields, card_name, comment='', ifile=None, is_list=True, has_none=True)
            continue
        elif keyi == 'is_enddata':
            model.card_count['ENDDATA'] = 1
            continue

        value = _cast(sub_group)
        try:
            setattr(model, keyi, value)
        except AttributeError:  # pragma: no cover
            model.log.warning('cant set minor_attributes/%s as %s' % (keyi, value))
            raise

    return


def _load_indexed_list(key, group, encoding):
    lst = []
    for key in group.keys():
        value = _cast(group[key])
        lst.append(value)
    #print('_load_indexed_list: %s' % lst)
    return lst

def _load_indexed_list_str(key, group, encoding):
    lst = _load_indexed_list(key, group, encoding)

    #try:
        #value0 = value[0]
    #except IndexError:  # pragma: no cover
        #print('key =', key)
        #print('value = %r' % value)
        #print('group =', group)
        #print('group.keys() =', list(group.keys()))
        #raise

    if isinstance(value, text_type):
        pass
    else:
        lst = [line.encode(encoding) for line in lst]
        assert isinstance(lst[0], text_type), type(lst[0])
    return lst

def hdf5_load_coords(model, coords_group, encoding):
    """loads the coords from an HDF5 file"""
    for card_type in coords_group.keys():
        coords = coords_group[card_type]
        if card_type in ['CORD2R', 'CORD2C', 'CORD2S']:
            if card_type == 'CORD2R':
                func = model.add_cord2r
            elif card_type == 'CORD2C':
                func = model.add_cord2c
            elif card_type == 'CORD2S':
                func = model.add_cord2s

            cids = _cast(coords['cid'])
            rids = _cast(coords['rid'])
            e1s = _cast(coords['e1'])
            e2s = _cast(coords['e2'])
            e3s = _cast(coords['e3'])
            for cid, rid, origin, zaxis, xzplane in zip(
                    cids, rids, e1s, e2s, e3s):
                func(cid, origin, zaxis, xzplane, rid=rid, comment='')
        elif card_type in ['CORD1R', 'CORD1C', 'CORD1S']:
            if card_type == 'CORD1R':
                func = model.add_cord1r
            elif card_type == 'CORD1C':
                func = model.add_cord1c
            elif card_type == 'CORD1S':
                func = model.add_cord1s

            cids = _cast(coords['cid'])
            nodes = _cast(coords['nodes'])
            for cid, (n1, n2, n3) in zip(cids, nodes):
                func(cid, n1, n2, n3, comment='')
        else:
            cids, values = load_cards_from_keys_values(
                'coords/%s' % card_type,
                coords, encoding, model.log)
            _put_keys_values_into_dict(model, 'coords', cids, values)
        model.card_count[card_type] = len(cids)

def hdf5_load_tables(model, group, encoding):
    """loads the tables"""
    for card_type in group.keys():
        sub_group = group[card_type]
        #if card_type == 'TABLES1':
            #pass
        keys, values = load_cards_from_keys_values(
            'tables/%s' % card_type,
            sub_group, encoding, model.log)
        _put_keys_values_into_dict(model, 'tables', keys, values)
        model.card_count[card_type] = len(keys)

def hdf5_load_methods(model, group, encoding):
    """loads the methods"""
    for card_type in group.keys():
        sub_group = group[card_type]
        #if card_type == 'EIGRL':
            #pass
        keys, values = load_cards_from_keys_values(
            'methods/%s' % card_type,
            sub_group, encoding, model.log)
        _put_keys_values_into_dict(model, 'methods', keys, values)
        model.card_count[card_type] = len(keys)

def hdf5_load_masses(model, group, encoding):
    """loads the masses"""
    for card_type in group.keys():
        masses = group[card_type]
        if card_type == 'CONM2':
            eid = _cast(masses['eid'])
            nid = _cast(masses['nid'])
            cid = _cast(masses['cid'])
            X = _cast(masses['X'])
            I = _cast(masses['I'])
            mass = _cast(masses['mass'])
            for eidi, nidi, cidi, Xi, Ii, massi in zip(eid, nid, cid, X, I, mass):
                model.add_conm2(eidi, nidi, massi, cid=cidi, X=Xi, I=Ii, comment='')
        elif card_type == 'CMASS2':
            eid = _cast(masses['eid'])
            mass = _cast(masses['mass'])
            nodes = _cast(masses['nodes']).tolist()
            components = _cast(masses['components'])
            for eidi, massi, nids, (c1, c2) in zip(eid, mass, nodes, components):
                model.add_cmass2(eidi, massi, nids, c1, c2, comment='')

        else:
            #model.add_cmass1(eid, pid, nids, c1=0, c2=0, comment='')
            #model.add_cmass3(eid, pid, nids, comment='')
            #model.add_cmass4(eid, mass, nids, comment='')
            #model.add_conm1(eid, nid, mass_matrix, cid=0, comment='')
            eid, values = load_cards_from_keys_values(
                'masses/%s' % card_type,
                masses, encoding, model.log)
            _put_keys_values_into_dict(model, 'masses', eid, values)
        model.card_count[card_type] = len(eid)


def hdf5_load_materials(model, group, encoding):
    """loads the materials"""
    for card_type in group.keys():
        sub_group = group[card_type]
        if card_type == 'MAT1':
            mid = _cast(sub_group['mid'])
            E = _cast(sub_group['E'])
            G = _cast(sub_group['G'])
            nu = _cast(sub_group['nu'])
            rho = _cast(sub_group['rho'])
            a = _cast(sub_group['A'])
            tref = _cast(sub_group['tref'])
            ge = _cast(sub_group['ge'])
            St = _cast(sub_group['St'])
            Sc = _cast(sub_group['Sc'])
            Ss = _cast(sub_group['Ss'])
            mcsid = _cast(sub_group['mcsid'])
            for midi, Ei, Gi, nui, rhoi, ai, trefi, gei, Sti, Sci, Ssi, mcsidi in zip(
                    mid, E, G, nu, rho, a, tref, ge, St, Sc, Ss, mcsid):
                model.add_mat1(midi, Ei, Gi, nui, rho=rhoi, a=ai, tref=trefi,
                               ge=gei, St=Sti, Sc=Sci, Ss=Ssi, mcsid=mcsidi, comment='')

        elif card_type == 'MAT2':
            mid = _cast(sub_group['mid'])
            G = _cast(sub_group['G'])
            rho = _cast(sub_group['rho'])
            a = _cast(sub_group['A'])
            tref = _cast(sub_group['tref'])
            ge = _cast(sub_group['ge'])
            St = _cast(sub_group['St'])
            Sc = _cast(sub_group['Sc'])
            Ss = _cast(sub_group['Ss'])
            mcsid = _cast(sub_group['mcsid'])

            for (midi, (G11, G22, G33, G12, G13, G23), rhoi, (a1i, a2i, a3i),
                 trefi, gei, Sti, Sci, Ssi, mcsidi) in zip(
                     mid, G, rho, a, tref, ge, St, Sc, Ss, mcsid):
                if mcsidi == -1:
                    mcsidi = None
                model.add_mat2(midi, G11, G12, G13, G22, G23, G33, rho=rhoi,
                               a1=a1i, a2=a2i, a3=a3i, tref=trefi, ge=gei,
                               St=Sti, Sc=Sci, Ss=Ssi, mcsid=mcsidi, comment='')

        elif card_type == 'MAT3':
            mid = _cast(sub_group['mid'])
            ex = _cast(sub_group['Ex'])
            eth = _cast(sub_group['Eth'])
            ez = _cast(sub_group['Ez'])

            nuxth = _cast(sub_group['Nuxth'])
            nuzx = _cast(sub_group['Nuzx'])
            nuthz = _cast(sub_group['Nuthz'])
            gxz = _cast(sub_group['Gzx'])

            ax = _cast(sub_group['Ax'])
            ath = _cast(sub_group['Ath'])
            az = _cast(sub_group['Az'])

            rho = _cast(sub_group['rho'])
            tref = _cast(sub_group['tref'])
            ge = _cast(sub_group['ge'])
            for (midi, exi, ethi, ezi, nuxthi, nuzxi, nuthzi,
                 rhoi, gzxi, axi, athi, azi, trefi, gei) in zip(
                     mid, ex, eth, ez, nuxth, nuzx, nuthz, rho, gxz, ax, ath, az, tref, ge):
                model.add_mat3(midi, exi, ethi, ezi, nuxthi, nuthzi, nuzxi, rho=rhoi,
                               gzx=gzxi, ax=axi, ath=athi, az=azi, tref=trefi, ge=gei, comment='')

        elif card_type == 'MAT8':
            mid = _cast(sub_group['mid'])
            e11 = _cast(sub_group['E11'])
            e22 = _cast(sub_group['E22'])
            nu12 = _cast(sub_group['Nu12'])
            g12 = _cast(sub_group['G12'])
            g1z = _cast(sub_group['G1z'])
            g2z = _cast(sub_group['G2z'])

            a1 = _cast(sub_group['A1'])
            a2 = _cast(sub_group['A2'])
            tref = _cast(sub_group['tref'])
            ge = _cast(sub_group['ge'])
            rho = _cast(sub_group['rho'])

            xt = _cast(sub_group['Xt'])
            xc = _cast(sub_group['Xc'])
            yt = _cast(sub_group['Yt'])
            yc = _cast(sub_group['Yc'])
            s = _cast(sub_group['S'])

            f12 = _cast(sub_group['F12'])
            strn = _cast(sub_group['strn'])
            for (midi, e11i, e22i, nu12i, g12i, g1zi, g2zi, rhoi, a1i, a2i, trefi,
                 xti, xci, yti, yci, si, gei, f12i, strni) in zip(
                     mid, e11, e22, nu12, g12, g1z, g2z, rho, a1, a2, tref,
                     xt, xc, yt, yc, s, ge, f12, strn):
                model.add_mat8(midi, e11i, e22i, nu12i, g12=g12i, g1z=g1zi, g2z=g2zi, rho=rhoi,
                               a1=a1i, a2=a2i, tref=trefi, Xt=xti, Xc=xci, Yt=yti, Yc=yci,
                               S=si, ge=gei, F12=f12i, strn=strni, comment='')
        elif card_type == 'MAT9':
            ## TODO: add G
            mid = _cast(sub_group['mid'])
            a = _cast(sub_group['A'])
            tref = _cast(sub_group['tref'])
            ge = _cast(sub_group['ge'])
            rho = _cast(sub_group['rho'])
            for midi, ai, trefi, gei, rhoi in zip(mid, a, tref, ge, rho):
                model.add_mat9(
                    midi,
                    G11=0., G12=0., G13=0., G14=0., G15=0., G16=0.,
                    G22=0., G23=0., G24=0., G25=0., G26=0.,
                    G33=0., G34=0., G35=0., G36=0.,
                    G44=0., G45=0., G46=0.,
                    G55=0., G56=0.,
                    G66=0.,
                    rho=rhoi, A=ai, tref=trefi, ge=gei, comment='')

        elif card_type in ['MAT8', 'MAT9']:
            model.log.warning('skipping materials/%s because its vectorized '
                              'and needs a loader' % card_type)
            continue
        else:
            #model.add_mat4(mid, k, cp=0.0, rho=1.0, H=None, mu=None, hgen=1.0,
                           #ref_enthalpy=None, tch=None, tdelta=None, qlat=None, comment='')
            #model.add_mat5(mid, kxx=0., kxy=0., kxz=0., kyy=0., kyz=0., kzz=0.,
                           #cp=0., rho=1., hgen=1., comment='')
            #model.add_mat10(mid, bulk, rho, c, ge=0.0, gamma=None,
                            #table_bulk=None, table_rho=None, table_ge=None,
                            #table_gamma=None, comment='')
            #model.add_mat11(mid, e1, e2, e3, nu12, nu13, nu23, g12, g13, g23,
                            #rho=0.0, a1=0.0, a2=0.0, a3=0.0, tref=0.0, ge=0.0, comment='')
            mid, values = load_cards_from_keys_values(
                'materials/%s' % card_type,
                sub_group, encoding, model.log)
            _put_keys_values_into_dict(model, 'materials', mid, values)
        model.card_count[card_type] = len(mid)

def hdf5_load_spcs(model, group, encoding):
    """loads the spcs"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for spc_id in keys:
        ispc_id = int(spc_id)
        cards_group = group[spc_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'SPC1':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'spcs/%s/%s' % (spc_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'spcs', ispc_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_spcadds(model, group, encoding):
    """loads the spcadds"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for spc_id in keys:
        ispc_id = int(spc_id)
        cards_group = group[spc_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'SPC1':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'spcadds/%s/%s' % (spc_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'spcadds', ispc_id, lkeys, values)

def hdf5_load_mpcs(model, group, encoding):
    """loads the mpcs"""
    keys = list(group.keys())
    keys.remove('keys')
    #mpc_ids = _cast(group['keys'])
    for mpc_id in keys:
        impc_id = int(mpc_id)
        cards_group = group[mpc_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'MPC':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'mpcs/%s/%s' % (mpc_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'mpcs', impc_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_mpcadds(model, group, encoding):
    """loads the mpcadds"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for mpc_id in keys:
        impc_id = int(mpc_id)
        cards_group = group[mpc_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'MPCADD':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'mpcadds/%s/%s' % (mpc_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'mpcadds', mpc_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_loads(model, group, encoding):
    """loads the loads"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for load_id in keys:
        iload_id = int(load_id)
        cards_group = group[load_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            if card_type in ['FORCE', 'MOMENT']:
                if card_type == 'FORCE':
                    func = model.add_force
                else:
                    func = model.add_moment
                sid = _cast(sub_group['sid'])
                node = _cast(sub_group['node'])
                cid = _cast(sub_group['cid'])
                mag = _cast(sub_group['mag'])
                xyz = _cast(sub_group['xyz'])
                for (sidi, nodei, magi, xyzi, cidi) in zip(sid, node, mag, xyz, cid):
                    func(sidi, nodei, magi, xyzi, cid=cidi, comment='')
            elif card_type == 'TEMP':  # this has a weird dictionary structure
                sid = sub_group.keys()
                for index in sid:
                    cardi = sub_group[index]
                    nodes = _cast(cardi['node']).tolist()
                    temp = _cast(cardi['temperature']).tolist()
                    temperatures = {nid : tempi for (nid, tempi) in zip(nodes, temp)}
                    card = model.add_temp(iload_id, temperatures, comment='')
            else:
                #model.add_force1(sid, node, mag, g1, g2, comment='')
                sid, values = load_cards_from_keys_values(
                    'loads/%s/%s' % (load_id, card_type),
                    sub_group, encoding, model.log)
                #for value in values:
                    #print(value)
                _put_keys_values_into_dict_list(model, 'loads', iload_id, sid, values)
            model.card_count[card_type] = len(sid)

def hdf5_load_load_combinations(model, group, encoding):
    """loads the load_combinations"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for load_id in keys:
        iload_id = int(load_id)
        cards_group = group[load_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'LOAD':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'load_combinations/%s/%s' % (load_id, card_type),
                sub_group, encoding, model.log)
            #for value in values:
                #print(value)
            _put_keys_values_into_dict_list(model, 'load_combinations', iload_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_nsms(model, group, encoding):
    """loads the nsms"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for nsm_id in keys:
        insm_id = int(nsm_id)
        cards_group = group[nsm_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'NSM':
                #mid = _cast(sub_group['mid'])
            #else:
            keys, values = load_cards_from_keys_values(
                'nsms/%s/%s' % (nsm_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'nsms', insm_id, keys, values)
            model.card_count[card_type] = len(keys)

def hdf5_load_nsmadds(model, group, encoding):
    """loads the nsmadds"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for nsm_id in keys:
        insm_id = int(nsm_id)
        cards_group = group[nsm_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'NSMADD':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'nsmadds/%s/%s' % (nsm_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'nsmadds', insm_id, lkeys, values)
            model.card_count[card_type] = len(keys)

def hdf5_load_frequencies(model, group, encoding):
    """loads the frequencies"""
    keys = list(group.keys())
    keys.remove('keys')
    #spc_ids = _cast(group['keys'])
    for freq_id in keys:
        ifreq_id = int(freq_id)
        cards_group = group[freq_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'FREQ':
                #mid = _cast(sub_group['mid'])
            #else:
            fkeys, values = load_cards_from_keys_values(
                'frequencies/%s/%s' % (freq_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'frequencies', ifreq_id, fkeys, values)
            model.card_count[card_type] = len(fkeys)

def hdf5_load_aelinks(model, group, encoding):
    """loads the aelinks"""
    keys = group.keys()
    naelinks = 0
    for aelink_id in keys:
        iaelink_id = int(aelink_id)
        jlinks_group = group[aelink_id]
        keys = jlinks_group.keys()
        aelink = [None] * len(keys)
        for jlink in keys:
            j_int = int(jlink)
            aelinki_group = jlinks_group[jlink]
            value = aelinki_group
            aelinki = _load_class(jlink, value, 'AELINK', encoding)
            aelink[j_int] = aelinki
            naelinks += 1
        for aelinki in aelink:
            model._add_aelink_object(aelinki)
    model.card_count['AELINK'] = naelinks

def hdf5_load_dloads(model, group, encoding):
    """loads the dloads"""
    keys = list(group.keys())
    keys.remove('keys')
    #dload_ids = _cast(group['keys'])
    for dload_id in keys:
        idload_id = int(dload_id)
        cards_group = group[dload_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'DLOAD':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'dloads/%s/%s' % (dload_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'dloads', idload_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_dload_entries(model, group, encoding):
    """loads the dload_entries"""
    keys = list(group.keys())
    keys.remove('keys')
    #dload_ids = _cast(group['keys'])
    for dload_id in keys:
        idload_id = int(dload_id)
        cards_group = group[dload_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'TLOAD1':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'dload_entries/%s/%s' % (dload_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'dload_entries', idload_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_bcs(model, group, encoding):
    """loads the bcs"""
    keys = list(group.keys())
    keys.remove('keys')
    #dload_ids = _cast(group['keys'])
    for bc_id in keys:
        ibc_id = int(bc_id)
        cards_group = group[bc_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'MAT1':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'bcs/%s/%s' % (bc_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'bcs', ibc_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_transfer_functions(model, group, encoding):
    """loads the transfer_functions"""
    keys = list(group.keys())
    keys.remove('keys')
    #dload_ids = _cast(group['keys'])
    for tf_id in keys:
        itf_id = int(tf_id)
        cards_group = group[tf_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'MAT1':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'transfer_functions/%s/%s' % (tf_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'transfer_functions', itf_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_dvgrids(model, group, encoding):
    """loads the dvgrids"""
    keys = list(group.keys())
    keys.remove('keys')
    #dload_ids = _cast(group['keys'])
    for opt_id in keys:
        iopt_id = int(opt_id)
        cards_group = group[opt_id]
        for card_type in cards_group.keys():
            sub_group = cards_group[card_type]
            #if card_type == 'MAT1':
                #mid = _cast(sub_group['mid'])
            #else:
            lkeys, values = load_cards_from_keys_values(
                'dvgrids/%s/%s' % (opt_id, card_type),
                sub_group, encoding, model.log)
            _put_keys_values_into_dict_list(model, 'dvgrids', iopt_id, lkeys, values)
            model.card_count[card_type] = len(lkeys)

def hdf5_load_desvars(model, group, encoding):
    """loads the desvars"""
    for card_type in group.keys():
        sub_group = group[card_type]
        if card_type == 'DESVAR':
            desvar = _cast(sub_group['desvar'])
            label = _cast(sub_group['label']).tolist()
            xinit = _cast(sub_group['xinit'])
            xlb = _cast(sub_group['xlb'])
            xub = _cast(sub_group['xub'])
            delx = _cast(sub_group['delx'])
            ddval = _cast(sub_group['ddval'])
            for desvari, labeli, xiniti, xlbi, xubi, delxi, ddvali in zip(
                desvar, label, xinit, xlb, xub, delx, ddval):
                labeli = labeli.decode(encoding)
                assert isinstance(labeli, text_type), labeli
                model.add_desvar(desvari, labeli, xiniti, xlb=xlbi, xub=xubi,
                   delx=delxi, ddval=ddvali, comment='')
        else:  # pragma: no cover
            raise RuntimeError('card_type=%s in hdf5_load_desvars' % card_type)
        model.card_count[card_type] = len(desvar)

def hdf5_load_dmigs(model, group, encoding):
    """loads the dmigs"""
    keys = group.keys()
    if len(keys) == 0:
        #model.log.warning('skipping loading %s' % group)
        raise RuntimeError('error loading %s' % group)
        #return

    for name in keys:
        sub_group = group[name]
        #print('group', group)
        #print('sub_group', sub_group)

        class_type = group.attrs['type']
        if class_type == 'DMIG' and name == 'UACCEL':
            uaccel
        elif class_type == 'DMI':
            ncols = _cast(sub_group['ncols'])
            nrows = _cast(sub_group['nrows'])
            #polar = _cast(sub_group['polar'])
            matrix_form = _cast(sub_group['matrix_form'])
            tin = _cast(sub_group['tin'])
            tout = _cast(sub_group['tout'])
            GCi = _cast(sub_group['GCi'])
            GCj = _cast(sub_group['GCj'])
            Real = _cast(sub_group['Real'])
            Complex = None
            if 'Complex' in sub_group:
                Complex = _cast(sub_group['Complex'])

            #ifo = matrix_form
            form = matrix_form
            model.add_dmi(name, form, tin, tout, nrows, ncols, GCj, GCi, Real, Complex=None, comment='')

        else:
            class_obj = CARD_MAP[class_type]
            ncols = None
            if 'ncols' in sub_group:
                ncols = _cast(sub_group['ncols'])
            polar = _cast(sub_group['polar'])
            matrix_form = _cast(sub_group['matrix_form'])
            tin = _cast(sub_group['tin'])
            tout = _cast(sub_group['tout'])
            #dmig_group.create_dataset('tin_dtype', data=dmig.tin_dtype)
            #dmig_group.create_dataset('tout_dtype', data=dmig.tout_dtype)

            #dmig_group.create_dataset('matrix_type', data=dmig.matrix_type)
            #dmig_group.create_dataset('is_complex', data=dmig.is_complex)
            #dmig_group.create_dataset('is_real', data=dmig.is_real)
            #dmig_group.create_dataset('is_polar', data=dmig.is_polar)

            GCi = _cast(sub_group['GCi'])
            GCj = _cast(sub_group['GCj'])
            Real = _cast(sub_group['Real'])
            Complex = None
            if 'Complex' in sub_group:
                Complex = _cast(sub_group['Complex'])

            ifo = matrix_form
            dmig = class_obj(name, ifo, tin, tout, polar, ncols,
                             GCj, GCi, Real, Complex=Complex, comment='', finalize=True)
            model.dmigs[name] = dmig
    model.card_count[class_type] = len(keys)

def hdf5_load_dconstrs(model, group, encoding):
    """loads the dconstrs"""
    keys = group.keys()
    if len(keys) == 0:
        #model.log.warning('skipping loading %s' % group)
        raise RuntimeError('error loading %s' % group)
        #return

    for card_type in keys:
        sub_group = group[card_type]
        #print('group', group)
        #print('sub_group', sub_group)

        if card_type == 'DCONSTR':
            #keys_group = list(sub_group.keys())
            oid = _cast(sub_group['oid'])
            dresp_id = _cast(sub_group['dresp_id'])
            lid = _cast(sub_group['lid'])
            uid = _cast(sub_group['uid'])
            lowfq = _cast(sub_group['lowfq'])
            highfq = _cast(sub_group['highfq'])

            for oidi, dresp_idi, lidi, uidi, lowfqi, highfqi in zip(oid, dresp_id, lid, uid, lowfq, highfq):
                model.add_dconstr(oidi, dresp_idi, lid=lidi, uid=uidi, lowfq=lowfqi, highfq=highfqi, comment='')

        elif card_type == 'DCONADD':
            keys = sub_group.keys()
            #print('keys_group', keys_group)

            debug = False
            name = 'dconstrs/%s' % card_type

            for key in keys:
                value = sub_group[key]
                dconadd = _load_class(key, value, card_type, encoding)
                model._add_dconstr_object(dconadd)
                #model.add_dconadd(oid, dconstrs, comment='')
        else:
            raise RuntimeError('error loading %s' % card_type)

        model.card_count[card_type] = len(keys)

def hdf5_load_usets(model, group, encoding):
    """loads the usets"""
    keys = group.keys()
    if len(keys) == 0:
        #model.log.warning('skipping loading %s' % group)
        raise RuntimeError('error loading %s' % group)
        #return

    for name in keys:
        sub_group = group[name]
        keys = sub_group.keys()
        lst = [None] * len(keys)

        for key in keys:
            sub_groupi = sub_group[key]
            keys2 = sub_groupi.keys()

            value = sub_groupi
            card_type = _cast(sub_groupi['type'])
            class_obj = _load_class(key, value, card_type, encoding)
            model._add_uset_object(class_obj)
            if card_type not in model.card_count:
                model.card_count[card_type] = 1
            else:
                model.card_count[card_type] += 1

def hdf5_load_dresps(model, group, encoding):
    """loads the dresps"""
    keys = list(group.keys())
    if len(keys) == 0:
        #model.log.warning('skipping loading %s' % group)
        raise RuntimeError('error loading %s' % group)
        #return

    for class_type in group.keys():
        sub_group = group[class_type]

        if class_type == 'DRESP1':
            keys_group = list(sub_group.keys())
            #print('keys_group', keys_group)

            #'atta', u'attb', u'dresp_id', u'label', u'region', u'response_type'
            dresp_id = _cast(sub_group['dresp_id'])
            atta = _cast(sub_group['atta']).tolist()
            #print('atta =', atta)
            attb = _cast(sub_group['attb']).tolist()
            label = _cast(sub_group['label'])
            region = _cast(sub_group['region'])
            response_type = _cast(sub_group['response_type'])
            property_type = _cast(sub_group['property_type'])
            atti = []
            for (i, dresp_idi, labeli, response_typei, property_typei, regioni,
                 attai, attbi) in zip(count(), dresp_id, label, response_type, property_type, region,
                                      atta, attb):
                drespi_group = sub_group[str(i)]

                labeli = labeli.decode(encoding)
                response_typei = response_typei.decode(encoding)

                if property_typei == b'':
                    property_typei = None
                elif property_typei.isdigit():
                    property_typei = int(property_typei)
                else:
                    property_typei = property_typei.decode(encoding)

                if regioni == -1:
                    regioni = None
                #else:
                    #regioni = regioni.decode(encoding)

                # int, float, str, blank
                if attai == b'':
                    attai = None
                elif b'.' in attai:
                    attai = float(attai)
                elif attai.isdigit():
                    attai = int(attai)
                else:
                    attai = attai.decode(encoding)

                # int, float, str, blank
                if attbi == b'':
                    attbi = None
                elif b'.' in attbi:
                    attbi = float(attbi)
                elif attbi.isdigit():
                    attbi = int(attbi)
                else:
                    attbi = attbi.decode(encoding)

                atti = []
                if 'atti' in drespi_group:
                    atti = _cast(drespi_group['atti']).tolist()

                model.add_dresp1(dresp_idi, labeli, response_typei, property_typei, regioni,
                                 attai, attbi, atti, validate=False, comment='')

        elif class_type == 'DRESP2':
            dresp_id = _cast(sub_group['dresp_id'])
            label = _cast(sub_group['label'])
            dequation = _cast(sub_group['dequation'])
            dequation_str = _cast(sub_group['func'])
            #dequation_str = _cast(sub_group['dequation_str'])
            region = _cast(sub_group['region'])
            method = _cast(sub_group['method'])
            c123 = _cast(sub_group['c123'])

            for (i, dresp_idi, labeli, dequationi, dequation_stri, regioni, methodi, (c1, c2, c3)) in zip(
                    count(), dresp_id, label, dequation, dequation_str, region, method, c123):

                if regioni == -1:
                    regioni = None
                #paramsi = {(0, u'DESVAR'): [1, 2, 3]}
                paramsi = {}
                dresp_groupi = sub_group[str(i)]
                param_keys = _cast(dresp_groupi['param_keys']).tolist()
                #print('param_keys', param_keys)

                for j in range(len(param_keys)):
                    param_values = _cast(dresp_groupi[str(j)]['values']).tolist()
                    param_key = param_keys[j].decode(encoding)
                    #print('  param_values', (i, j), param_values)
                    param_values2 = [val.decode(encoding) if isinstance(val, binary_type) else val
                                     for val in param_values]
                    paramsi[(j, param_key)] = param_values2
                model.log.debug('DRESP2 params = %s' % paramsi)

                if dequationi == -1:
                    dequationi = dequation_stri.decode(encoding)

                labeli = labeli.decode(encoding)
                methodi = methodi.decode(encoding)
                model.add_dresp2(dresp_idi, labeli, dequationi, regioni, paramsi,
                                 method=methodi, c1=c1, c2=c2, c3=c3,
                                 validate=False, comment='')
        else:
            raise RuntimeError('error loading %s' % class_type)

        model.card_count[class_type] = len(dresp_id)

def hdf5_load_generic(model, group, name, encoding):
    for card_type in group.keys():
        sub_group = group[card_type]
        #if card_type == 'TABLES1':
            #pass
        lkeys, values = load_cards_from_keys_values(
            '%s/%s' % (name, card_type),
            sub_group, encoding, model.log)
        _put_keys_values_into_dict(model, name, lkeys, values)
        model.card_count[card_type] = len(lkeys)


def hdf5_load_properties(model, properties_group, encoding):
    """loads the properties from an HDF5 file"""
    for card_type in properties_group.keys():
        properties = properties_group[card_type]
        if card_type == 'PSHELL':
            pid = _cast(properties['pid'])
            mids = _cast(properties['mids'])
            z = _cast(properties['z'])
            t = _cast(properties['t'])
            twelveIt3 = _cast(properties['twelveIt3'])
            tst = _cast(properties['tst'])
            nsm = _cast(properties['nsm'])
            for pidi, (mid1, mid2, mid3, mid4), (z1, z2), ti, twelveIt3i, tsti, nsmi in zip(
                    pid, mids, z, t, twelveIt3, tst, nsm):
                if np.isnan(ti):
                    ti = None
                    raise RuntimeError('Differential shell thickness is not supported')
                if np.isnan(z1):
                    z1 = None
                if np.isnan(z2):
                    z2 = None
                model.add_pshell(pidi, mid1=mid1, t=ti, mid2=mid2, twelveIt3=twelveIt3i,
                                 mid3=mid3, tst=tsti, nsm=nsmi, z1=z1, z2=z2, mid4=mid4,
                                 comment='')
        elif card_type in ['PSOLID', 'PIHEX']:
            func = model.add_psolid if card_type == 'PSOLID' else model.add_pihex
            pid = _cast(properties['pid'])
            mid = _cast(properties['mid'])
            cordm = _cast(properties['cordm'])
            integ = _cast(properties['integ'])
            isop = _cast(properties['isop'])
            stress = _cast(properties['stress'])
            fctn = _cast(properties['fctn'])
            for pidi, midi, cordmi, integi, stressi, isopi, fctni in zip(
                    pid, mid, cordm, integ, stress, isop, fctn):
                integi = integi.decode(encoding)
                fctni = fctni.decode(encoding)
                isopi = isopi.decode(encoding)
                stressi = stressi.decode(encoding)
                if integi == '':
                    integi = None
                if fctni == '':
                    fctni = None
                if isopi == '':
                    isopi = None
                if stressi == '':
                    stressi = None
                func(pidi, midi, cordm=cordmi, integ=integi, stress=stressi,
                     isop=isopi, fctn=fctni, comment='')

        elif card_type == 'PROD':
            pid = _cast(properties['pid'])
            mid = _cast(properties['mid'])
            A = _cast(properties['A'])
            j = _cast(properties['J'])
            c = _cast(properties['c'])
            nsm = _cast(properties['nsm'])
            for pidi, midi, Ai, ji, ci, nsmi in zip(
                    pid, mid, A, j, c, nsm):
                model.add_prod(pidi, midi, Ai, j=ji, c=ci, nsm=nsmi, comment='')

        elif card_type == 'PTUBE':
            pid = _cast(properties['pid'])
            mid = _cast(properties['mid'])
            OD = _cast(properties['OD'])
            t = _cast(properties['t'])
            nsm = _cast(properties['nsm'])
            for pidi, midi, (OD1, OD2), ti, nsmi in zip(
                    pid, mid, OD, t, nsm):
                model.add_ptube(pidi, midi, OD1, t=ti, nsm=nsmi, OD2=OD2, comment='')

        elif card_type == 'PBAR':
            pid = _cast(properties['pid'])
            mid = _cast(properties['mid'])
            A = _cast(properties['A'])
            J = _cast(properties['J'])
            I = _cast(properties['I'])

            c = _cast(properties['c'])
            d = _cast(properties['d'])
            e = _cast(properties['e'])
            f = _cast(properties['f'])
            k = _cast(properties['k'])

            nsm = _cast(properties['nsm'])
            for (pidi, midi, Ai, Ji, (i1, i2, i12),
                 (c1, c2), (d1, d2), (e1, e2), (f1, f2), (k1, k2), nsmi) in zip(
                     pid, mid, A, J, I,
                     c, d, e, f, k, nsm):
                if k1 == np.nan:
                    k1 = None
                if k2 == np.nan:
                    k2 = None
                model.add_pbar(pidi, midi, A=Ai, i1=i1, i2=i2, i12=i12, j=Ji, nsm=nsmi,
                               c1=c1, c2=c2, d1=d1, d2=d2, e1=e1, e2=e2,
                               f1=f1, f2=f2, k1=k1, k2=k2, comment='')
        else:
            debug = False
            #if card_type == 'PCOMP':
                #debug = True
            pid, values = load_cards_from_keys_values(
                'properties/%s' % card_type,
                properties, encoding, model.log, debug=debug)
            _put_keys_values_into_dict(model, 'properties', pid, values)

            #model.add_pshear(pid, mid, t, nsm=0., f1=0., f2=0., comment='')
            #model.add_pvisc(pid, ce, cr, comment='')
            #model.add_pelas(pid, k, ge=0., s=0., comment='')
            #model.add_pdamp(pid, b, comment='')
            #model.add_pcomp(pid, mids, thicknesses, thetas=None, souts=None, nsm=0., sb=0.,
                            #ft=None, tref=0., ge=0., lam=None, z0=None, comment='')
            #model.add_pcompg(pid, global_ply_ids, mids, thicknesses, thetas=None, souts=None,
                             #nsm=0.0, sb=0.0, ft=None, tref=0.0, ge=0.0, lam=None, z0=None,
                             #comment='')
        model.card_count[card_type] = len(pid)

    for prop in model.properties.values():
        write_card(prop)

def _put_keys_values_into_dict(model, name, keys, values, cast_int_keys=True):
    """add something like an element to a dictionary"""
    for value in values:
        write_card(value)

    slot = getattr(model, name)
    card_count = model.card_count
    if cast_int_keys and name not in ['dscreen', 'dti', 'aecomps']: # 'dmigs', 'dmiks', 'dmijs', 'dmijis', 'dmis'
        try:
            keys = [int(key) for key in keys]
        except ValueError:  # pragma: no cover
            print('name =', name)
            print('keys = ', keys)
            print('values = ', values)
            raise

    for key, value in zip(keys, values):
        slot[key] = value
        #print('  *%s %s' % (value.type, key))
        Type = value.type
        if Type not in card_count:
            card_count[Type] = 0
        card_count[Type] += 1
        model._type_to_id_map[Type].append(key)

def _put_keys_values_into_list(model, name, keys, values):
    """add something like an MKAERO1 to a list"""
    for value in values:
        write_card(value)

    slot = getattr(model, name)
    card_count = model.card_count
    for key, value in zip(keys, values):
        slot.append(value)
        #print('  *%s %s' % (value.type, key))
        Type = value.type
        if Type not in card_count:
            card_count[Type] = 0
        card_count[Type] += 1
        model._type_to_id_map[Type].append(key)

def _put_keys_values_into_dict_list(model, name, idi, keys, values):
    """add someting like an SPC into a dictionary that has a list"""
    for value in values:
        #print(value)
        write_card(value)

    slot = getattr(model, name)
    idi = int(idi)
    #assert isinstance(idi, int), 'idi=%s type=%s' % (idi, type(idi))
    if idi in slot:
        slot_list = slot[idi]
    else:
        slot_list = []
        slot[idi] = slot_list

    card_count = model.card_count
    for key, value in zip(keys, values):
        slot_list.append(value)
        #print('  *%s %s' % (value.type, key))
        Type = value.type
        if Type not in card_count:
            card_count[Type] = 0
        card_count[Type] += 1
        model._type_to_id_map[Type].append(key)

def load_cards_from_keys_values(name, properties, encoding, log, debug=False):
    try:
        keys = _cast(properties['keys'])
    except KeyError:  # pragma: no cover
        print('name = %s' % name)
        print(properties)
        raise
    #except TypeError:  # pragma: no cover
        #print('name = %s' % name)
        #print(properties)
        #print(properties['keys'])
        #raise
    values = properties['values']
    value_objs = _load_cards_from_keys_values(name, values, keys, encoding, log, debug=debug)
    return keys, value_objs

def _load_cards_from_keys_values(name, values, keys, encoding, log, debug=False):
    value_objs = []
    for key, keyi in zip(keys, values.keys()):
        #print('%s - %s' % (name, key))
        value = values[keyi]
        card_type = _cast(value['type'])
        class_instance = _load_class(key, value, card_type, encoding)
        value_objs.append(class_instance)
    return value_objs

def _load_class(key, value, card_type, encoding):
    keys_to_read = list(value.keys())
    class_obj = CARD_MAP[card_type]
    if hasattr(class_obj, '_init_from_empty'):
        class_instance = class_obj._init_from_empty()
    else:
        try:
            class_instance = class_obj()
        except TypeError:  # pragma: no cover
            print('error loading %r' % card_type)
            print(class_obj)
            raise

    _properties = []
    if hasattr(class_obj, '_properties'):
        _properties = class_obj._properties

    #print('  keys_to_read = ', keys_to_read)
    for key_to_cast in keys_to_read:
        if key_to_cast in _properties:
            continue

        valuei = _get_casted_value(value, key_to_cast, encoding)
        if isinstance(valuei, np.ndarray):
            valuei = valuei.tolist()
        try:
            setattr(class_instance, key_to_cast, valuei)
            #print('  set %s to %s' % (key_to_cast, valuei))
        except AttributeError:  # pragma: no cover
            print('error loading %r' % card_type)
            print(_properties)
            print(key, key_to_cast, valuei)
            raise
    #if debug:
        #print(class_instance.get_stats())
        #print(class_instance)
    if hasattr(class_instance, '_finalize_hdf5'):
        class_instance._finalize_hdf5(encoding)
    #else:
        #print('no %s' % class_instance.type)
    str(class_instance)
    return class_instance

def _get_casted_value(value, key_to_cast, encoding):
    value_h5 = value[key_to_cast]
    if isinstance(value_h5, h5py._hl.dataset.Dataset):
        valuei = _cast(value_h5)
        #print(key_to_cast, valuei, type(valuei))
    else:
        h5_keys = list(value_h5.keys())
        if len(h5_keys) == 0:
            valuei = _cast(value_h5)
        else:
            #print('h5_keys =', h5_keys)
            lst = []
            for h5_key in h5_keys:
                slot_h5 = value_h5[h5_key]

                if isinstance(slot_h5, h5py._hl.dataset.Dataset):
                    valueii = _cast(slot_h5)
                elif isinstance(slot_h5, h5py._hl.group.Group):
                    valueii = _load_indexed_list(h5_key, slot_h5, encoding)
                else:  # pragma: no cover
                    print(key_to_cast, h5_key)
                    print(slot_h5, type(slot_h5))
                    raise NotImplementedError()

                if isinstance(valueii, binary_type):
                    valueii = valueii.decode(encoding)
                elif isinstance(valueii, np.ndarray):
                    valueii = valueii.tolist()
                    if isinstance(valueii[0], binary_type):
                        valueii = [val.decode(encoding) if isinstance(val, binary_type) else val
                                   for val in valueii]

                lst.append(valueii)
            valuei = lst

        #valuei = None
    #else:
    #try:
        #valuei = _cast(value_h5)
    #except AttributeError:
        #print(value, key_to_cast, value.keys())
        #print(value_h5, value_h5.keys())
        #raise
        #valuei = None
    return valuei

def _load_from_class(value, card_type, encoding):
    keys_to_read = list(value.keys())
    class_obj = CARD_MAP[card_type]
    if hasattr(class_obj, '_init_from_empty'):
        class_instance = class_obj._init_from_empty()
    else:
        try:
            class_instance = class_obj()
        except TypeError:  # pragma: no cover
            print('error loading %r' % card_type)
            print(class_obj)
            raise

    _properties = []
    if hasattr(class_obj, '_properties'):
        _properties = class_obj._properties

    for key_to_cast in keys_to_read:
        if key_to_cast in _properties:
            continue

        valuei = _get_casted_value(value, key_to_cast, encoding)
        #print('%s set to %s' % (key_to_cast, valuei))
        #h5_value = value[key_to_cast]
        #try:
            #valuei = _cast(h5_value)
        #except AttributeError:
            #print('key =', key)
            #raise
            #valuei = None

        try:
            setattr(class_instance, key_to_cast, valuei)
        except AttributeError:  # pragma: no cover
            print('error loading %r' % card_type)
            print(_properties)
            print(key_to_cast, valuei)
            raise

    if hasattr(class_instance, '_finalize_hdf5'):
        class_instance._finalize_hdf5(encoding)
    return class_instance


def hdf5_load_elements(model, elements_group, encoding):
    """loads the elements from an HDF5 file"""
    for card_type in elements_group.keys():
        elements = elements_group[card_type]
        if card_type == 'CTETRA':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                model.add_ctetra(eid, pid, nids, comment='')
        elif card_type == 'CPENTA':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                model.add_cpenta(eid, pid, nids, comment='')
        elif card_type == 'CPYRAM':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                model.add_cpyram(eid, pid, nids, comment='')
        elif card_type == 'CHEXA':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                model.add_chexa(eid, pid, nids, comment='')

        elif card_type == 'CROD':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                model.add_crod(eid, pid, nids, comment='')
        elif card_type == 'CTUBE':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                model.add_ctube(eid, pid, nids, comment='')
        elif card_type == 'CONROD':
            eids = _cast(elements['eid'])
            mids = _cast(elements['mid'])
            nodes = _cast(elements['nodes']).tolist()
            A = _cast(elements['A'])
            J = _cast(elements['J'])
            c = _cast(elements['c'])
            nsm = _cast(elements['nsm'])
            for eid, mid, nids, ai, ji, ci, nsmi in zip(eids, mids, nodes, A, J, c, nsm):
                model.add_conrod(eid, mid, nids, A=ai, j=ji, c=ci, nsm=nsmi, comment='')

        elif card_type == 'CBAR':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            g0 = _cast(elements['g0'])
            x = _cast(elements['x'])
            offt = _cast(elements['offt'])
            wa = _cast(elements['wa'])
            wb = _cast(elements['wb'])
            pa = _cast(elements['pa'])
            pb = _cast(elements['pb'])
            for eid, pid, nids, xi, g0i, offti, pai, pbi, wai, wbi in zip(
                    eids, pids, nodes, x, g0, offt, pa, pb, wa, wb):
                if g0i == -1:
                    g0i = None
                if xi[0] == np.nan:
                    xi = [None, None, None]
                model.add_cbar(eid, pid, nids, xi, g0i, offt=offti.decode(encoding),
                               pa=pai, pb=pbi, wa=wai, wb=wbi, comment='')

        elif card_type == 'CBEAM':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            g0 = _cast(elements['g0'])
            x = _cast(elements['x'])
            bit = _cast(elements['bit'])
            offt = _cast(elements['offt'])
            sa = _cast(elements['sa'])
            sb = _cast(elements['sb'])
            wa = _cast(elements['wa'])
            wb = _cast(elements['wb'])
            pa = _cast(elements['pa'])
            pb = _cast(elements['pb'])
            for eid, pid, nids, xi, g0i, offti, biti, pai, pbi, wai, wbi, sai, sbi in zip(
                    eids, pids, nodes, x, g0, offt, bit, pa, pb, wa, wb, sa, sb):
                if g0i == -1:
                    g0i = None
                if xi[0] == np.nan:
                    xi = [None, None, None]
                if biti == np.nan:
                    offti = offti.decode(encoding)
                else:
                    offti = None
                model.add_cbeam(eid, pid, nids, xi, g0i, offt=offti, bit=biti,
                                pa=pai, pb=pbi, wa=wai, wb=wbi, sa=sai, sb=sbi, comment='')

        elif card_type in ['CELAS1', 'CDAMP1']:
            func = model.add_celas1 if card_type == 'CELAS1' else model.add_cdamp1
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            components = _cast(elements['components'])
            for eid, pid, nids, (c1, c2) in zip(eids, pids, nodes, components):
                func(eid, pid, nids, c1=c1, c2=c2, comment='')
        elif card_type == 'CELAS2':
            eids = _cast(elements['eid'])
            k = _cast(elements['K'])
            ge = _cast(elements['ge'])
            s = _cast(elements['s'])
            nodes = _cast(elements['nodes']).tolist()
            components = _cast(elements['components'])
            for eid, ki, nids, (c1, c2), gei, si in zip(eids, k, nodes, components, ge, s):
                model.add_celas2(eid, ki, nids, c1=c1, c2=c2, ge=gei, s=si, comment='')
        elif card_type == 'CDAMP2':
            eids = _cast(elements['eid'])
            b = _cast(elements['B'])
            nodes = _cast(elements['nodes']).tolist()
            components = _cast(elements['components'])
            for eid, bi, nids, (c1, c2) in zip(eids, b, nodes, components):
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_cdamp2(eid, bi, nids, c1=c1, c2=c2, comment='')

        elif card_type in ['CELAS3', 'CDAMP3', 'CDAMP5', 'CVISC']:
            if card_type == 'CELAS3':
                func = model.add_celas3
            elif card_type == 'CDAMP3':
                func = model.add_cdamp3
            elif card_type == 'CDAMP5':
                func = model.add_cdamp5
            elif card_type == 'CVISC':
                func = model.add_cvisc
            else:
                raise NotImplementedError(card_type)
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_celas3(eid, pid, nids, comment='')
        elif card_type == 'CELAS4':
            eids = _cast(elements['eid'])
            k = _cast(elements['K'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, ki, nids in zip(eids, k, nodes):
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_celas4(eid, ki, nids, comment='')
        elif card_type == 'CDAMP4':
            eids = _cast(elements['eid'])
            b = _cast(elements['B'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, bi, nids in zip(eids, b, nodes):
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_cdamp4(eid, bi, nids, comment='')


        elif card_type == 'CBUSH':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            g0 = _cast(elements['g0'])
            x = _cast(elements['x']).tolist()
            cid = _cast(elements['cid'])
            ocid = _cast(elements['ocid'])
            s = _cast(elements['s'])
            si = _cast(elements['si']).tolist()
            for eid, pid, nids, xi, g0i, cidi, s2, ocidi, si2 in zip(
                    eids, pids, nodes, x, g0, cid, s, ocid, si):
                nids = list([nid if nid != 0 else None for nid in nids])
                if g0i == -1:
                    g0i = None
                #if xi[0] == np.nan:
                    #xi = [None, None, None]
                if cidi == -1:
                    cidi = None

                if si2[0] == np.nan:
                    si2 = [None, None, None]
                elem = model.add_cbush(eid, pid, nids, xi, g0i, cid=cidi, s=s2, ocid=ocidi, si=si2,
                                       comment='')
                write_card(elem)

        elif card_type == 'CGAP':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            g0 = _cast(elements['g0'])
            x = _cast(elements['x']).tolist()
            cid = _cast(elements['cid'])
            for eid, pid, nids, xi, g0i, cidi in zip(
                    eids, pids, nodes, x, g0, cid):
                nids = list([nid if nid != 0 else None for nid in nids])
                if g0i == -1:
                    g0i = None
                #if xi[0] == np.nan:
                    #xi = [None, None, None]
                if cidi == -1:
                    cidi = None
                elem = model.add_cgap(eid, pid, nids, xi, g0i, cid=cidi, comment='')
                #write_card(elem)

        elif card_type == 'CBUSH1D':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            cid = _cast(elements['cid'])
            for eid, pid, nids, cidi in zip(eids, pids, nodes, cid):
                nids = list([nid if nid != 0 else None for nid in nids])
                if cidi == -1:
                    cidi = None
                model.add_cbush1d(eid, pid, nids, cid=cidi, comment='')

        elif card_type in ['CTRIA3', 'CTRIAR']:
            func = model.add_ctria3 if card_type == 'CTRIA3' else model.add_ctriar
            # TODO: doesn't support tflag
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            mcids = _cast(elements['mcid'])
            zoffsets = _cast(elements['zoffset'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, mcid, theta, zoffset in zip(
                    eids, pids, nodes, mcids, thetas, zoffsets):
                if mcid == -1:
                    theta_mcid = theta
                else:
                    theta_mcid = mcid
                model.add_ctria3(eid, pid, nids, zoffset=zoffset, theta_mcid=theta_mcid,
                                 tflag=0, T1=None, T2=None, T3=None, comment='')
        elif card_type in ['CQUAD4', 'CQUADR']:
            func = model.add_cquad4 if card_type == 'CQUAD4' else model.add_cquadr
            # TODO: doesn't support tflag
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            mcids = _cast(elements['mcid'])
            zoffsets = _cast(elements['zoffset'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, mcid, theta, zoffset in zip(
                    eids, pids, nodes, mcids, thetas, zoffsets):
                if mcid == -1:
                    theta_mcid = theta
                else:
                    theta_mcid = mcid
                func(eid, pid, nids, zoffset=zoffset, theta_mcid=theta_mcid,
                     tflag=0, T1=None, T2=None, T3=None, T4=None, comment='')

        elif card_type == 'CTRIA6':
            # TODO: doesn't support tflag
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            mcids = _cast(elements['mcid'])
            zoffsets = _cast(elements['zoffset'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, mcid, theta, zoffset in zip(
                    eids, pids, nodes, mcids, thetas, zoffsets):
                if mcid == -1:
                    theta_mcid = theta
                else:
                    theta_mcid = mcid
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_ctria6(eid, pid, nids, zoffset=zoffset, theta_mcid=theta_mcid,
                                 tflag=0, T1=None, T2=None, T3=None, comment='')
        elif card_type == 'CQUAD8':
            # TODO: doesn't support tflag
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            mcids = _cast(elements['mcid'])
            zoffsets = _cast(elements['zoffset'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, mcid, theta, zoffset in zip(
                    eids, pids, nodes, mcids, thetas, zoffsets):
                if mcid == -1:
                    theta_mcid = theta
                else:
                    theta_mcid = mcid
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_cquad8(eid, pid, nids, zoffset=zoffset, theta_mcid=theta_mcid,
                                 tflag=0, T1=None, T2=None, T3=None, T4=None, comment='')

        elif card_type == 'CQUAD':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            mcids = _cast(elements['mcid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, mcid, theta in zip(eids, pids, nodes, mcids, thetas):
                if mcid == -1:
                    theta_mcid = theta
                else:
                    theta_mcid = mcid
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_cquad(eid, pid, nids, theta_mcid=theta_mcid, comment='')

        elif card_type == 'CSHEAR':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids in zip(eids, pids, nodes):
                model.add_cshear(eid, pid, nids, comment='')

        elif card_type == 'CTRIAX':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            mcids = _cast(elements['mcid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, mcid, theta in zip(eids, pids, nodes, mcids, thetas):
                if mcid == -1:
                    theta_mcid = theta
                else:
                    theta_mcid = mcid
                model.add_ctriax(eid, pid, nids, theta_mcid=theta_mcid, comment='')
        elif card_type == 'CTRAX3':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, theta in zip(eids, pids, nodes, thetas):
                model.add_ctrax3(eid, pid, nids, theta=theta, comment='')
        elif card_type == 'CTRAX6':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, theta in zip(eids, pids, nodes, thetas):
                model.add_ctrax6(eid, pid, nids, theta=theta, comment='')
        elif card_type == 'CTRIAX6':
            eids = _cast(elements['eid'])
            mids = _cast(elements['mid'])
            thetas = _cast(elements['theta'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, mid, nids, theta in zip(eids, mids, nodes, thetas):
                nids = list([nid if nid != 0 else None for nid in nids])
                model.add_ctriax6(eid, mid, nids, theta=theta, comment='')

        elif card_type == 'CQUADX':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            mcids = _cast(elements['mcid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, theta, mcid in zip(eids, pids, nodes, thetas, mcids):
                if mcid == -1:
                    theta_mcid = theta
                else:
                    theta_mcid = mcid
                nids = [None if nid == 0 else nid
                        for nid in nids]
                model.add_cquadx(eid, pid, nids, theta_mcid=theta_mcid, comment='')

        elif card_type == 'CQUADX4':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, theta in zip(eids, pids, nodes, thetas):
                model.add_cquadx4(eid, pid, nids, theta=theta, comment='')
        elif card_type == 'CQUADX8':
            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, theta in zip(eids, pids, nodes, thetas):
                model.add_cquadx8(eid, pid, nids, theta=theta, comment='')

        elif card_type in ['CPLSTN3', 'CPLSTN4']:
            func = model.add_cplstn3 if card_type == 'CPLSTN3' else model.add_cplstn4

            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, theta in zip(eids, pids, nodes, thetas):
                func(eid, pid, nids, theta=theta, comment='')
        elif card_type in ['CPLSTN6', 'CPLSTN8']:
            func = model.add_cplstn6 if card_type == 'CPLSTN6' else model.add_cplstn8

            eids = _cast(elements['eid'])
            pids = _cast(elements['pid'])
            thetas = _cast(elements['theta'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, pid, nids, theta in zip(eids, pids, nodes, thetas):
                func(eid, pid, nids, theta=theta, comment='')
        else:
            eids, values = load_cards_from_keys_values(
                'elements/%s' % card_type,
                elements, encoding, model.log)
            _put_keys_values_into_dict(model, 'elements', eids, values)
            #model.add_cdamp4(eid, b, nids, comment='')
            #model.add_cbush2d(eid, pid, nids, cid=0, plane='XY', sptid=None, comment='')
            #model.add_cfast(eid, pid, Type, ida, idb, gs=None, ga=None, gb=None,
                            #xs=None, ys=None, zs=None, comment='')
            #model.add_cmass1(eid, pid, nids, c1=0, c2=0, comment='')
            #model.add_cmass2(eid, mass, nids, c1, c2, comment='')
            #model.add_cmass3(eid, pid, nids, comment='')
            #model.add_cmass4(eid, mass, nids, comment='')
            #model.log.debug(card_type)
        model.card_count[card_type] = len(eids)

def hdf5_load_plotels(model, elements_group, encoding):
    """loads the plotels from an HDF5 file"""
    for card_type in elements_group.keys():
        elements = elements_group[card_type]
        if card_type == 'PLOTEL':
            eids = _cast(elements['eid'])
            nodes = _cast(elements['nodes']).tolist()
            for eid, nids in zip(eids, nodes):
                model.add_plotel(eid, nids, comment='')
        else:  # pragma: no cover
            raise RuntimeError('card_type=%s in hdf5_load_plotels' % card_type)
        model.card_count[card_type] = len(eids)

def write_card(elem):  # pragma: no cover
    """verifies that the card was built correctly near where the card was made"""
    try:
        elem.write_card()
    except:  # pragma: no cover
        print(elem.get_stats())
        raise
