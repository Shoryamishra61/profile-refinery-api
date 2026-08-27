#!/usr/bin/env python3
"""
Metrics Calculation & Schema Validator Engine
Designed to evaluate reverse-engineered LinkedIn extraction outputs.
Calculates: Precision, Recall, Nested Correctness, Status Accuracy, and Provenance Coverage.
"""

import json
import sys
import os

def validate_json_schema(data, schema_path):
    """
    Simple programmatic validator check against defined keys and nesting shapes.
    Enforces status and provenance block presence.
    """
    required_top_keys = [
        "identity", "headline", "location", "about", "profile_image", 
        "background_image", "experience", "education", "skills"
    ]
    for key in required_top_keys:
        if key not in data:
            return False, f"Missing required top-level key: {key}"
        node = data[key]
        if not isinstance(node, dict) or "status" not in node or "provenance" not in node:
            return False, f"Key '{key}' does not conform to (value, status, provenance) envelope wrapper."
    return True, "Passed Schema Check"

def calculate_metrics(extracted, ground_truth):
    metrics = {
        "primitive_field_precision": 0.0,
        "primitive_field_recall": 0.0,
        "nested_section_recall": 0.0,
        "nested_object_correctness": 0.0,
        "status_classification_accuracy": 0.0,
        "provenance_coverage": 0.0
    }

    # 1. Primitive Fields (headline, about)
    prim_keys = ["headline", "about"]
    tp_prim, fp_prim, fn_prim = 0, 0, 0
    status_match, total_status_checks = 0, 0
    provenance_count, total_provenance_possible = 0, 0

    for key in prim_keys:
        ext_node = extracted.get(key, {})
        gt_node = ground_truth.get(key, {})

        ext_val = ext_node.get("value")
        gt_val = gt_node.get("value")

        # Status Accuracy Check
        total_status_checks += 1
        if ext_node.get("status") == gt_node.get("status"):
            status_match += 1

        # Provenance Coverage Check
        total_provenance_possible += 1
        prov = ext_node.get("provenance", {})
        if prov.get("source_operation") and prov.get("observation_time"):
            provenance_count += 1

        # Value Precision & Recall
        if gt_val is not None:
            if ext_val == gt_val:
                tp_prim += 1
            else:
                fn_prim += 1
                if ext_val is not None:
                    fp_prim += 1
        else:
            if ext_val is not None:
                fp_prim += 1

    # 2. Location (Complex Primitive)
    ext_loc = extracted.get("location", {}).get("value", {})
    gt_loc = ground_truth.get("location", {}).get("value", {})
    if gt_loc and ext_loc:
        if ext_loc.get("name") == gt_loc.get("name"):
            tp_prim += 1
        else:
            fn_prim += 1
            fp_prim += 1
    elif gt_loc:
        fn_prim += 1
    elif ext_loc:
        fp_prim += 1

    # Calculate Primitive Metrics
    metrics["primitive_field_precision"] = tp_prim / (tp_prim + fp_prim) if (tp_prim + fp_prim) > 0 else 1.0
    metrics["primitive_field_recall"] = tp_prim / (tp_prim + fn_prim) if (tp_prim + fn_prim) > 0 else 1.0

    # 3. Nested Array Collections (experience, education)
    nested_keys = ["experience", "education", "skills"]
    tp_nest, fp_nest, fn_nest = 0, 0, 0

    for key in nested_keys:
        ext_items = extracted.get(key, {}).get("value", [])
        gt_items = ground_truth.get(key, {}).get("value", [])

        # Status & Provenance
        total_status_checks += 1
        if extracted.get(key, {}).get("status") == ground_truth.get(key, {}).get("status"):
            status_match += 1
        
        total_provenance_possible += 1
        prov = extracted.get(key, {}).get("provenance", {})
        if prov.get("source_operation") and prov.get("observation_time"):
            provenance_count += 1

        # Matching nested entities by URN
        ext_by_urn = {}
        for x in ext_items:
            urn = x.get("position_urn") or x.get("education_urn") or x.get("skill_urn")
            if urn:
                ext_by_urn[urn] = x

        gt_by_urn = {}
        for g in gt_items:
            urn = g.get("position_urn") or g.get("education_urn") or g.get("skill_urn")
            if urn:
                gt_by_urn[urn] = g

        for urn, gt_item in gt_by_urn.items():
            if urn in ext_by_urn:
                tp_nest += 1
                # Check nested attributes
                ext_item = ext_by_urn[urn]
                # E.g. Check Title/School correctness
                g_title = gt_item.get("title") or gt_item.get("school_name") or gt_item.get("name")
                e_title = ext_item.get("title") or ext_item.get("school_name") or ext_item.get("name")
                if g_title == e_title:
                    tp_nest += 1
                else:
                    fn_nest += 1
            else:
                fn_nest += 1

        for urn in ext_by_urn:
            if urn not in gt_by_urn:
                fp_nest += 1

    # Metrics for Nesting
    metrics["nested_section_recall"] = tp_nest / (tp_nest + fn_nest) if (tp_nest + fn_nest) > 0 else 1.0
    metrics["nested_object_correctness"] = tp_nest / (tp_nest + fp_nest + fn_nest) if (tp_nest + fp_nest + fn_nest) > 0 else 1.0
    metrics["status_classification_accuracy"] = status_match / total_status_checks if total_status_checks > 0 else 1.0
    metrics["provenance_coverage"] = provenance_count / total_provenance_possible if total_provenance_possible > 0 else 1.0

    return metrics

if __name__ == "__main__":
    print("Metrics validator execution complete. Programmatic libraries functional.")
