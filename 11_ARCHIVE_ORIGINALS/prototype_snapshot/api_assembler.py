from typing import Dict, List, Any, Optional

class EntityAssembler:
    """
    Parses and de-normalizes flat, relational JSON-LD structured REST/GraphQL arrays.
    Reassembles the entity graph using stable URN references (e.g. mapping ProfilePictures
    to original digitalmediaAsset download URLs, or pairing positions with company details).
    """
    
    @staticmethod
    def assemble_entities(raw_payload: Dict[str, Any], target_urn: str) -> Dict[str, Any]:
        """
        Processes the flat relational 'included' array, linking items back to the parent profile.
        Returns a structured, unified dictionary containing nested collections.
        """
        # Search for 'included' array at the top level or nested inside data blocks
        included = raw_payload.get("included")
        if included is None:
            # Fallback 1: Nested in voyagerIdentityDashProfiles
            included = raw_payload.get("data", {}).get("voyagerIdentityDashProfiles", {}).get("included")
        if included is None:
            # Fallback 2: Nested in identityDashProfilesByMemberIdentity
            included = raw_payload.get("data", {}).get("identityDashProfilesByMemberIdentity", {}).get("included")
        if included is None:
            included = []
        
        # Build lookup tables for fast entity linking
        positions: List[Dict[str, Any]] = []
        educations: List[Dict[str, Any]] = []
        skills: List[Dict[str, Any]] = []
        certifications: List[Dict[str, Any]] = []
        languages: List[Dict[str, Any]] = []
        companies: Dict[str, Dict[str, Any]] = {}
        profile_pictures: Dict[str, Dict[str, Any]] = {}
        profile_entity: Optional[Dict[str, Any]] = None
        
        # Search for elements at various typical structures
        elements = raw_payload.get("data", {}).get("voyagerIdentityDashProfiles", {}).get("elements", [])
        if not elements:
            elements = raw_payload.get("data", {}).get("identityDashProfilesByMemberIdentity", {}).get("elements", [])
        if not elements:
            elements = raw_payload.get("elements", [])
        primary_element = elements[0] if elements else {}
        
        for item in included:
            urn = item.get("entityUrn", "")
            item_type = item.get("$type", "")
            
            # Identify core Profile entity
            if urn == target_urn or item_type == "com.linkedin.voyager.dash.identity.Profile":
                profile_entity = item
                
            # Classify relational collections
            elif "fsd_profilePosition" in urn or "fs_position" in urn or item_type == "com.linkedin.voyager.dash.identity.Position":
                positions.append(item)
                
            elif "fsd_profileEducation" in urn or "fs_education" in urn or item_type == "com.linkedin.voyager.dash.identity.Education":
                educations.append(item)
                
            elif "fsd_profileSkill" in urn or "fs_skill" in urn or item_type == "com.linkedin.voyager.dash.identity.Skill":
                skills.append(item)
                
            elif "fsd_profileCertification" in urn or "fs_certification" in urn or item_type == "com.linkedin.voyager.dash.identity.Certification":
                certifications.append(item)
                
            elif "fsd_profileLanguage" in urn or "fs_language" in urn or item_type == "com.linkedin.voyager.dash.identity.Language":
                languages.append(item)
                
            elif "fs_company" in urn or "fsd_company" in urn or item_type == "com.linkedin.voyager.dash.entities.Company":
                companies[urn] = item
                
            elif "digitalmediaAsset" in urn or item_type == "com.linkedin.voyager.dash.identity.ProfilePicture":
                profile_pictures[urn] = item

        # If profile_entity was not found in 'included' but exists in elements, use that
        if not profile_entity and primary_element:
            profile_entity = primary_element
            
        # Fallback to empty dictionary if still missing
        if not profile_entity:
            profile_entity = {}

        # Resolve relational references: Join Positions with Companies
        resolved_positions = []
        for pos in positions:
            company_urn = pos.get("companyUrn") or pos.get("*company")
            company_details = companies.get(company_urn, {}) if company_urn else {}
            
            resolved_pos = {
                "position_urn": pos.get("entityUrn"),
                "title": pos.get("title"),
                "company_name": pos.get("companyName") or company_details.get("name"),
                "company_urn": company_urn,
                "start_date": pos.get("timePeriod", {}).get("startDate") or pos.get("dateRange", {}).get("start"),
                "end_date": pos.get("timePeriod", {}).get("endDate") or pos.get("dateRange", {}).get("end"),
                "location_name": pos.get("locationName"),
                "description": pos.get("description"),
                "grouped_promotions": []
            }
            resolved_positions.append(resolved_pos)
            
        # Resolve Profile Picture download details cleanly
        profile_img_meta = None
        profile_pic_node = profile_entity.get("profilePicture") or {}
        pic_urn_node = profile_pic_node.get("displayImage") or {}
        
        # Extract picture URN string or inline details
        if isinstance(pic_urn_node, dict):
            pic_urn = pic_urn_node.get("vectorArtifact")
            elements_list = pic_urn_node.get("elements", [])
            if elements_list:
                img_url = elements_list[0].get("downloadUrl")
                expires_at = elements_list[0].get("expiresAt")
                if img_url:
                    profile_img_meta = {
                        "raw_cdn_url": img_url,
                        "vector_artifact_id": pic_urn or "urn:li:digitalmediaAsset:inline",
                        "expires_at": expires_at
                    }
        else:
            pic_urn = pic_urn_node
            
        if not profile_img_meta and pic_urn and pic_urn in profile_pictures:
            pic_node = profile_pictures[pic_urn]
            cropped_img = pic_node.get("croppedImage") or pic_node.get("displayImage") or {}
            
            # Some nodes have subelements
            elements_list = cropped_img.get("elements", []) if isinstance(cropped_img, dict) else []
            if elements_list:
                img_url = elements_list[0].get("downloadUrl")
                expires_at = elements_list[0].get("expiresAt")
            else:
                img_url = cropped_img.get("downloadUrl") if isinstance(cropped_img, dict) else None
                expires_at = cropped_img.get("downloadUrlExpiresAt") or cropped_img.get("expiresAt") if isinstance(cropped_img, dict) else None
                
            if img_url:
                profile_img_meta = {
                    "raw_cdn_url": img_url,
                    "vector_artifact_id": pic_urn,
                    "expires_at": expires_at
                }
                
        # Resolve Background Picture details cleanly
        bg_img_meta = None
        bg_pic_node = profile_entity.get("backgroundPicture") or {}
        bg_urn_node = bg_pic_node.get("originalImage") or {}
        
        if isinstance(bg_urn_node, dict):
            bg_urn = bg_urn_node.get("vectorArtifact")
            elements_list = bg_urn_node.get("elements", [])
            if elements_list:
                bg_url = elements_list[0].get("downloadUrl")
                expires_at = elements_list[0].get("expiresAt")
                if bg_url:
                    bg_img_meta = {
                        "raw_cdn_url": bg_url,
                        "vector_artifact_id": bg_urn or "urn:li:digitalmediaAsset:inline",
                        "expires_at": expires_at
                    }
        else:
            bg_urn = bg_urn_node
            
        if not bg_img_meta and bg_urn and bg_urn in profile_pictures:
            bg_node = profile_pictures[bg_urn]
            cropped_bg = bg_node.get("croppedImage") or bg_node.get("displayImage") or {}
            
            bg_url = cropped_bg.get("downloadUrl") if isinstance(cropped_bg, dict) else None
            expires_at = cropped_bg.get("downloadUrlExpiresAt") or cropped_bg.get("expiresAt") if isinstance(cropped_bg, dict) else None
            if bg_url:
                bg_img_meta = {
                    "raw_cdn_url": bg_url,
                    "vector_artifact_id": bg_urn,
                    "expires_at": expires_at
                }

        return {
            "profile": profile_entity,
            "positions": resolved_positions,
            "educations": educations,
            "skills": skills,
            "certifications": certifications,
            "languages": languages,
            "profile_image": profile_img_meta,
            "background_image": bg_img_meta
        }
