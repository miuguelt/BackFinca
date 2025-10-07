from typing import Dict, List, Optional, Tuple
from flask import current_app
from app import db, cache
from app.models.animals import Animals
from app.models.breeds import Breeds
import sqlalchemy as sa
import time
import hashlib


def _serialize(animal: Animals, fields: Optional[List[str]] = None) -> Dict:
    if not animal:
        return {}
    base = {
        'id': animal.id,
        'record': animal.record,
        'sex': str(animal.sex) if getattr(animal, 'sex', None) is not None else None,
        'breeds_id': animal.breeds_id,
        'idFather': animal.idFather,
        'idMother': animal.idMother,
    }
    if not fields:
        return base
    return {k: base.get(k) for k in fields if k in base}


def _cache_key(kind: str, root_id: int, max_depth: int, fields: Optional[List[str]]) -> str:
    fields_sig = ''
    if fields:
        try:
            fields_sig = hashlib.sha1((','.join(sorted(fields))).encode('utf-8')).hexdigest()[:10]
        except Exception:
            fields_sig = 'fields'
    return f"animal_tree:{kind}:{root_id}:d{max_depth}:{fields_sig}"


def _cache_timeout() -> int:
    try:
        return int(current_app.config.get('CACHE_DEFAULT_TIMEOUT', 600))
    except Exception:
        return 600


def build_ancestor_tree(root_id: int, max_depth: int = 5, fields: Optional[List[str]] = None) -> Dict:
    """Construye árbol de ancestros (padre y madre por niveles) con caché."""
    key = _cache_key('ancestors', root_id, max_depth, fields)
    cached = cache.get(key)
    if cached:
        return cached

    nodes: Dict[int, Dict] = {}
    edges: List[Dict] = []
    depth = 0

    root: Animals = db.session.get(Animals, root_id)
    if not root:
        return {'rootId': root_id, 'nodes': {}, 'edges': [], 'depth': 0, 'counts': {'nodes': 0, 'edges': 0}}

    nodes[root.id] = _serialize(root, fields)
    current_ids = [root.id]

    while current_ids and depth < max_depth:
        # Recoger padres de este nivel en lote
        parent_ids: List[int] = []
        children_for_parent: List[Tuple[int, Optional[int], Optional[int]]] = []
        for cid in current_ids:
            child = db.session.get(Animals, cid)
            if not child:
                continue
            children_for_parent.append((cid, child.idFather, child.idMother))
            if child.idFather:
                parent_ids.append(child.idFather)
            if child.idMother:
                parent_ids.append(child.idMother)

        # Prefetch padres en un solo query
        parent_ids = list({pid for pid in parent_ids if pid})
        if not parent_ids:
            break
        parents: List[Animals] = db.session.query(Animals).filter(Animals.id.in_(parent_ids)).all()
        for p in parents:
            if p.id not in nodes:
                nodes[p.id] = _serialize(p, fields)

        # Agregar edges child -> padre/madre y preparar siguiente nivel
        next_ids: List[int] = []
        for cid, fid, mid in children_for_parent:
            if fid and fid in nodes:
                edges.append({'from': fid, 'to': cid, 'relation': 'father'})
                next_ids.append(fid)
            if mid and mid in nodes:
                edges.append({'from': mid, 'to': cid, 'relation': 'mother'})
                next_ids.append(mid)

        current_ids = list({nid for nid in next_ids})
        depth += 1

    # Summary y ejemplos de edges por sexo/especie
    # Calcular conteos por sexo
    sex_counts: Dict[str, int] = {'Macho': 0, 'Hembra': 0, 'Unknown': 0}
    for n in nodes.values():
        sex = n.get('sex')
        if sex in ('Macho', 'Hembra'):
            sex_counts[sex] += 1
        else:
            sex_counts['Unknown'] += 1

    # Mapear breeds_id -> species_id en un solo query
    breed_ids = list({n.get('breeds_id') for n in nodes.values() if n.get('breeds_id') is not None})
    species_by_breed: Dict[int, int] = {}
    if breed_ids:
        try:
            for bid, sid in db.session.query(Breeds.id, Breeds.species_id).filter(Breeds.id.in_(breed_ids)).all():
                species_by_breed[bid] = sid
        except Exception:
            pass

    # Conteos por especie basados en breeds
    species_counts: Dict[str, int] = {}
    for n in nodes.values():
        bid = n.get('breeds_id')
        sid = species_by_breed.get(bid)
        key = str(sid) if sid is not None else 'Unknown'
        species_counts[key] = species_counts.get(key, 0) + 1

    # Ejemplos de edges por sexo (sexo del nodo origen)
    edge_examples_by_sex: Dict[str, List[Dict]] = {'Macho': [], 'Hembra': [], 'Unknown': []}
    # Ejemplos de edges por especie (especie del nodo origen)
    edge_examples_by_species: Dict[str, List[Dict]] = {}
    for e in edges:
        src = nodes.get(e.get('from'))
        if not src:
            continue
        src_sex = src.get('sex') if src.get('sex') in ('Macho', 'Hembra') else 'Unknown'
        if len(edge_examples_by_sex[src_sex]) < 5:
            edge_examples_by_sex[src_sex].append({'from': e.get('from'), 'to': e.get('to'), 'relation': e.get('relation')})
        bid = src.get('breeds_id')
        sid = species_by_breed.get(bid)
        sp_key = str(sid) if sid is not None else 'Unknown'
        examples = edge_examples_by_species.setdefault(sp_key, [])
        if len(examples) < 5:
            examples.append({'from': e.get('from'), 'to': e.get('to'), 'relation': e.get('relation')})

    # Texto preformateado de resumen para UI
    total_nodes = len(nodes)
    total_edges = len(edges)
    summary_text = (
        f"Árbol de ancestros (root={root.id}): nodos={total_nodes}, edges={total_edges}; "
        f"sexo: Macho={sex_counts.get('Macho', 0)}, Hembra={sex_counts.get('Hembra', 0)}, Unknown={sex_counts.get('Unknown', 0)}; "
        f"especies={', '.join([f'{k}:{v}' for k, v in species_counts.items()])}"
    )

    result = {
        'rootId': root.id,
        'nodes': nodes,
        'edges': edges,
        'depth': depth,
        'counts': {'nodes': total_nodes, 'edges': total_edges},
        'summary': {
            'text': summary_text,
            'sex': sex_counts,
            'species': species_counts,
            'relations': {
                'father': sum(1 for e in edges if e.get('relation') == 'father'),
                'mother': sum(1 for e in edges if e.get('relation') == 'mother'),
            }
        },
        'edge_examples': {
            'bySex': edge_examples_by_sex,
            'bySpecies': edge_examples_by_species,
        },
        'generated_at': int(time.time())
    }
    cache.set(key, result, timeout=_cache_timeout())
    return result


def build_descendant_tree(root_id: int, max_depth: int = 5, fields: Optional[List[str]] = None) -> Dict:
    """Construye árbol de descendientes (hijos por niveles) con caché."""
    key = _cache_key('descendants', root_id, max_depth, fields)
    cached = cache.get(key)
    if cached:
        return cached

    nodes: Dict[int, Dict] = {}
    edges: List[Dict] = []
    depth = 0

    root: Animals = db.session.get(Animals, root_id)
    if not root:
        return {'rootId': root_id, 'nodes': {}, 'edges': [], 'depth': 0, 'counts': {'nodes': 0, 'edges': 0}}

    nodes[root.id] = _serialize(root, fields)
    current_ids = [root.id]

    while current_ids and depth < max_depth:
        # Buscar hijos donde padre o madre está en current_ids en un solo query
        children: List[Animals] = (
            db.session.query(Animals)
            .filter(sa.or_(Animals.idFather.in_(current_ids), Animals.idMother.in_(current_ids)))
            .all()
        )

        if not children:
            break

        next_ids: List[int] = []
        for child in children:
            if child.id not in nodes:
                nodes[child.id] = _serialize(child, fields)
            # edges desde padre/madre hacia el hijo
            if child.idFather and child.idFather in nodes:
                edges.append({'from': child.idFather, 'to': child.id, 'relation': 'father'})
            if child.idMother and child.idMother in nodes:
                edges.append({'from': child.idMother, 'to': child.id, 'relation': 'mother'})
            next_ids.append(child.id)

        current_ids = list({nid for nid in next_ids})
        depth += 1

    # Summary y ejemplos de edges por sexo/especie
    sex_counts: Dict[str, int] = {'Macho': 0, 'Hembra': 0, 'Unknown': 0}
    for n in nodes.values():
        sex = n.get('sex')
        if sex in ('Macho', 'Hembra'):
            sex_counts[sex] += 1
        else:
            sex_counts['Unknown'] += 1

    breed_ids = list({n.get('breeds_id') for n in nodes.values() if n.get('breeds_id') is not None})
    species_by_breed: Dict[int, int] = {}
    if breed_ids:
        try:
            for bid, sid in db.session.query(Breeds.id, Breeds.species_id).filter(Breeds.id.in_(breed_ids)).all():
                species_by_breed[bid] = sid
        except Exception:
            pass

    species_counts: Dict[str, int] = {}
    for n in nodes.values():
        bid = n.get('breeds_id')
        sid = species_by_breed.get(bid)
        key = str(sid) if sid is not None else 'Unknown'
        species_counts[key] = species_counts.get(key, 0) + 1

    edge_examples_by_sex: Dict[str, List[Dict]] = {'Macho': [], 'Hembra': [], 'Unknown': []}
    edge_examples_by_species: Dict[str, List[Dict]] = {}
    for e in edges:
        src = nodes.get(e.get('from'))
        if not src:
            continue
        src_sex = src.get('sex') if src.get('sex') in ('Macho', 'Hembra') else 'Unknown'
        if len(edge_examples_by_sex[src_sex]) < 5:
            edge_examples_by_sex[src_sex].append({'from': e.get('from'), 'to': e.get('to'), 'relation': e.get('relation')})
        bid = src.get('breeds_id')
        sid = species_by_breed.get(bid)
        sp_key = str(sid) if sid is not None else 'Unknown'
        examples = edge_examples_by_species.setdefault(sp_key, [])
        if len(examples) < 5:
            examples.append({'from': e.get('from'), 'to': e.get('to'), 'relation': e.get('relation')})

    total_nodes = len(nodes)
    total_edges = len(edges)
    summary_text = (
        f"Árbol de descendientes (root={root.id}): nodos={total_nodes}, edges={total_edges}; "
        f"sexo: Macho={sex_counts.get('Macho', 0)}, Hembra={sex_counts.get('Hembra', 0)}, Unknown={sex_counts.get('Unknown', 0)}; "
        f"especies={', '.join([f'{k}:{v}' for k, v in species_counts.items()])}"
    )

    result = {
        'rootId': root.id,
        'nodes': nodes,
        'edges': edges,
        'depth': depth,
        'counts': {'nodes': total_nodes, 'edges': total_edges},
        'summary': {
            'text': summary_text,
            'sex': sex_counts,
            'species': species_counts,
            'relations': {
                'father': sum(1 for e in edges if e.get('relation') == 'father'),
                'mother': sum(1 for e in edges if e.get('relation') == 'mother'),
            }
        },
        'edge_examples': {
            'bySex': edge_examples_by_sex,
            'bySpecies': edge_examples_by_species,
        },
        'generated_at': int(time.time())
    }
    cache.set(key, result, timeout=_cache_timeout())
    return result


def invalidate_animal_tree_cache_for(root_id: int):
    """Invalida entradas de caché para un animal específico (ambos tipos)."""
    try:
        # No tenemos listado de keys, usar patrones conocidos
        # Flask-Caching con Redis soporta delete_many para claves exactas.
        # Generamos un conjunto de claves comunes para profundidades típicas.
        depths = [1, 2, 3, 4, 5, 6]
        for d in depths:
            for kind in ('ancestors', 'descendants'):
                key = _cache_key(kind, root_id, d, None)
                try:
                    cache.delete(key)
                except Exception:
                    pass
    except Exception:
        pass


def invalidate_all_animal_trees():
    """Invalida árboles globalmente (mejor usar invalidate_animal_tree_cache_for tras cambios puntuales)."""
    # Si el backend usa Redis exclusivo para el cache, limpiar todo podría afectar otras vistas.
    # Evitamos cache.clear() global y dejamos invalidación por clave.
    pass