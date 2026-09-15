"""Omega AI v3 — Professional Assistance
Domain-specific support for all professions.
"""
from __future__ import annotations

from typing import Any


class ProfessionalAssist:
    """Multi-professional domain assistance."""

    DOMAINS: dict[str, dict[str, Any]] = {
        "software_eng": {"name": "Software Engineering", "description": "Design, develop, and maintain software systems.", "common": ["Code review", "Architecture design", "Debugging", "Testing", "CI/CD"], "concepts": ["SOLID", "Design Patterns", "Microservices", "REST APIs", "Agile"]},
        "data_science": {"name": "Data Science", "description": "Extract insights from data using statistics and ML.", "common": ["EDA", "Feature engineering", "Model selection", "Visualization", "Deployment"], "concepts": ["Overfitting", "Cross-validation", "Bias-Variance", "Pandas", "Scikit-learn"]},
        "ai_ml": {"name": "AI / Machine Learning", "description": "Build intelligent systems that learn from data.", "common": ["Neural networks", "NLP", "Computer vision", "MLOps", "Fine-tuning"], "concepts": ["Transformers", "Backpropagation", "Gradient descent", "Attention", "LLMs"]},
        "devops": {"name": "DevOps / SRE", "description": "Bridge development and operations for reliability.", "common": ["Infrastructure as Code", "Monitoring", "Incident response", "Automation", "Containerization"], "concepts": ["Docker", "Kubernetes", "Terraform", "Prometheus", "GitOps"]},
        "cybersecurity": {"name": "Cybersecurity", "description": "Protect systems and data from threats.", "common": ["Penetration testing", "Threat modeling", "Incident response", "Security audit", "Compliance"], "concepts": ["Zero Trust", "OWASP", "SIEM", "Encryption", "Phishing"]},
        "mechanical_eng": {"name": "Mechanical Engineering", "description": "Design mechanical systems and thermal devices.", "common": ["Stress analysis", "CAD modeling", "Thermodynamics", "FEA", "Manufacturing"], "concepts": ["Hooke's Law", "Bernoulli", "Heat transfer", "Tolerances", "GD&T"]},
        "electrical_eng": {"name": "Electrical Engineering", "description": "Design electrical systems, circuits, and power systems.", "common": ["Circuit design", "Power systems", "Control systems", "PCB layout", "Signal processing"], "concepts": ["Ohm's Law", "Kirchhoff", "FFT", "Three-phase", "Transformers"]},
        "civil_eng": {"name": "Civil Engineering", "description": "Design infrastructure: roads, bridges, buildings, water systems.", "common": ["Structural analysis", "Surveying", "Concrete design", "Hydrology", "Project management"], "concepts": ["Moment distribution", "Soil mechanics", "Reinforcement", "Drainage", "Load factors"]},
        "architecture": {"name": "Architecture", "description": "Design buildings and spaces for human use.", "common": ["Space planning", "3D modeling", "Material selection", "Building codes", "Client presentations"], "concepts": ["Form follows function", "Sustainability", "BIM", "Urban context", "Accessibility"]},
        "accounting": {"name": "Accounting", "description": "Record, classify, and report financial transactions.", "common": ["Bookkeeping", "Financial statements", "Audit", "Tax preparation", "Budgeting"], "concepts": ["GAAP/IFRS", "Double-entry", "Accrual", "Depreciation", "Reconciliation"]},
        "marketing": {"name": "Marketing", "description": "Promote products/services to target audiences.", "common": ["Campaign planning", "Content creation", "Analytics", "SEO/SEM", "Social media"], "concepts": ["4Ps", "Customer journey", "CPC/CPM", "A/B testing", "ROI"]},
        "hr": {"name": "Human Resources", "description": "Manage people, culture, and organizational development.", "common": ["Recruitment", "Performance management", "Training", "Compliance", "Employee relations"], "concepts": ["OKRs", "Engagement", "Labor law", "Diversity", "Retention"]},
        "legal": {"name": "Legal / Law", "description": "Provide legal advice and representation.", "common": ["Contract review", "Research", "Compliance", "Litigation support", "Drafting"], "concepts": ["Precedent", "Due process", "Liability", "Jurisdiction", "Discovery"], "disclaimer": "This is general information only, not legal advice. Consult a licensed attorney."},
        "medical_info": {"name": "Medical / Healthcare", "description": "General health information and guidance.", "common": ["Symptom assessment", "Medication info", "Preventive care", "Chronic disease management"], "concepts": ["Evidence-based medicine", "Vital signs", "Informed consent", "HIPAA/confidentiality"], "disclaimer": "This is general health information only, not medical advice. Consult a licensed healthcare professional."},
        "education": {"name": "Education / Teaching", "description": "Facilitate learning and educational development.", "common": ["Lesson planning", "Assessment", "Classroom management", "Curriculum design", "Differentiation"], "concepts": ["Bloom's taxonomy", "Formative assessment", "Pedagogy", "Learning styles", "UDL"]},
        "agriculture": {"name": "Agriculture", "description": "Cultivate crops and raise livestock for food and resources.", "common": ["Crop management", "Soil analysis", "Irrigation", "Pest control", "Harvest planning"], "concepts": ["Crop rotation", "pH levels", "Organic farming", "Precision agriculture", "Agribusiness"]},
        "plumbing": {"name": "Plumbing", "description": "Install and repair water, drainage, and gas systems.", "common": ["Pipe fitting", "Leak repair", "Drain cleaning", "Fixture installation", "Water heater service"], "concepts": ["Pressure", "Flow rate", "PVC/Copper/Pex", "Venting", "Code compliance"], "safety": "Always shut off water before repairs. Wear PPE. Gas work requires licensed professional."},
        "electrical_work": {"name": "Electrical Work", "description": "Install and maintain electrical wiring and systems.", "common": ["Wiring installation", "Troubleshooting", "Panel work", "Lighting", "Safety inspections"], "concepts": ["Voltage/Current", "Wire gauges", "Conduit", "GFCI/AFCI", "NEC/SANS codes"], "safety": "ALWAYS turn off power at breaker. Test with multimeter. Use insulated tools. Licensed work may be required by law."},
        "carpentry": {"name": "Carpentry", "description": "Work with wood to build structures and furniture.", "common": ["Framing", "Cabinetry", "Finish work", "Repairs", "Custom builds"], "concepts": ["Joinery", "Wood types", "Measurements", "Power tools", "Finishes"], "safety": "Wear safety glasses. Use push sticks. Keep guards in place. Unplug tools when changing blades."},
        "auto_mechanics": {"name": "Auto Mechanics", "description": "Diagnose and repair vehicles.", "common": ["Engine repair", "Brake service", "Diagnostics", "Maintenance", "Electrical"], "concepts": ["OBD-II", "Torque specs", "Fluid types", "Timing", "Suspension geometry"], "safety": "Use jack stands, never jacks alone. Wear gloves and eye protection. Disconnect battery before electrical work."},
        "tailoring": {"name": "Tailoring / Fashion Design", "description": "Create and alter clothing.", "common": ["Pattern making", "Alterations", "Fitting", "Sewing", "Design"], "concepts": ["Fabrics", "Measurements", "Darts", "Seam allowances", "Grain line"]},
        "culinary": {"name": "Culinary Arts", "description": "Prepare food professionally.", "common": ["Menu planning", "Prep work", "Cooking techniques", "Plating", "Kitchen management"], "concepts": ["Mise en place", "Mother sauces", "Temperature control", "Flavor profiles", "Food safety (HACCP)"], "safety": "Keep temperatures out of danger zone (5-60°C). Wash hands. Separate raw/cooked. Label everything."},
        "project_management": {"name": "Project Management", "description": "Plan and execute projects within constraints.", "common": ["Planning", "Scheduling", "Risk management", "Stakeholder communication", "Budgeting"], "concepts": ["Critical path", "WBS", "Gantt", "Agile/Scrum", "Triple constraint"]},
        "nursing": {"name": "Nursing", "description": "Provide patient care and health education.", "common": ["Patient assessment", "Medication administration", "Wound care", "Documentation", "Patient education"], "concepts": ["Nursing process", "Vital signs", "Infection control", "Scope of practice", "Evidence-based care"], "disclaimer": "This is general information only, not medical advice. Follow your facility's protocols."},
        "pharmacy": {"name": "Pharmacy", "description": "Dispense medications and counsel patients.", "common": ["Dispensing", "Drug interaction checks", "Counseling", "Inventory", "Compounding"], "concepts": ["Pharmacokinetics", "Therapeutic index", "Contraindications", "Generic substitution", "Cold chain"], "disclaimer": "This is general information only. Always consult a pharmacist or physician for medication advice."},
    }

    CODE_TEMPLATES: dict[str, str] = {
        "python": "def main():\n    pass\n\nif __name__ == '__main__':\n    main()",
        "javascript": "function main() {\n    console.log('Hello');\n}\n\nmain();",
        "java": "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello\");\n    }\n}",
        "cpp": "#include <iostream>\n\nint main() {\n    std::cout << \"Hello\" << std::endl;\n    return 0;\n}",
        "sql": "SELECT * FROM table_name\nWHERE condition = 'value'\nORDER BY column;",
    }

    def get_help(self, domain: str, query: str) -> str:
        """Get professional domain help."""
        domain_info = self._resolve_domain(domain)
        if not domain_info:
            return f"Domain '{domain}' not found. Available: {', '.join(self.list_domains())}"

        lines = [f"## {domain_info['name']}", f"{domain_info['description']}", ""]
        lines.append(f"**Common tasks:** {', '.join(domain_info.get('common', []))}")
        lines.append(f"**Key concepts:** {', '.join(domain_info.get('concepts', []))}")

        if "safety" in domain_info:
            lines.append(f"\n⚠️ **Safety:** {domain_info['safety']}")
        if "disclaimer" in domain_info:
            lines.append(f"\n⚠️ **Disclaimer:** {domain_info['disclaimer']}")

        lines.append(f"\n**Your query:** {query}")
        lines.append(f"\nFor this specific query, consider:")
        lines.append(f"1. Consulting industry standards and best practices")
        lines.append(f"2. Reviewing relevant documentation")
        lines.append(f"3. Seeking mentorship from experienced professionals")

        return "\n".join(lines)

    def list_domains(self) -> list[str]:
        """List available professional domains."""
        return [f"{k}: {v['name']}" for k, v in self.DOMAINS.items()]

    def code_assist(self, language: str, task: str) -> str:
        """Programming help."""
        lang = language.lower()
        template = self.CODE_TEMPLATES.get(lang, "# Template not available")

        lines = [f"## {language.title()} Assistance: {task}", ""]
        lines.append(f"**Starter template:**")
        lines.append(f"```{language}")
        lines.append(template)
        lines.append("```")
        lines.append(f"\n**Approach:**")
        lines.append(f"1. Break the task into smaller functions")
        lines.append(f"2. Write tests first (TDD)")
        lines.append(f"3. Handle errors gracefully")
        lines.append(f"4. Add comments and documentation")
        lines.append(f"5. Optimize only after it works")

        if lang == "python":
            lines.append(f"\n**Python best practices:**")
            lines.append(f"- Use type hints (Python 3.11+)")
            lines.append(f"- Follow PEP 8 style")
            lines.append(f"- Use virtual environments")
            lines.append(f"- Handle exceptions specifically")

        return "\n".join(lines)

    def engineering_calcs(self, discipline: str, inputs: dict[str, float]) -> str:
        """Engineering calculations."""
        disc = discipline.lower()
        lines = [f"## {discipline.title()} Calculations", ""]

        if "mechanical" in disc or "stress" in disc:
            force = inputs.get("force_n", 1000)
            area = inputs.get("area_mm2", 100)
            stress = force / area if area else 0
            lines.append(f"Stress = Force / Area = {force}N / {area}mm² = {stress:.2f} MPa")
            if stress < 250:
                lines.append("✓ Within typical steel yield limit")
            else:
                lines.append("⚠ Exceeds typical mild steel yield (250 MPa)")

        elif "electrical" in disc or "ohm" in disc:
            v = inputs.get("voltage", 12)
            r = inputs.get("resistance", 4)
            i = v / r if r else 0
            p = v * i
            lines.append(f"Current (I) = V/R = {v}V / {r}Ω = {i:.2f}A")
            lines.append(f"Power (P) = V×I = {v}V × {i:.2f}A = {p:.2f}W")

        elif "civil" in disc or "concrete" in disc:
            length = inputs.get("length_m", 5)
            width = inputs.get("width_m", 3)
            depth = inputs.get("depth_m", 0.15)
            volume = length * width * depth
            lines.append(f"Concrete volume = {length}m × {width}m × {depth}m = {volume:.2f} m³")
            lines.append(f"Add 10% wastage: {volume * 1.1:.2f} m³")

        else:
            lines.append(f"Calculations for {discipline}:")
            lines.append(f"Inputs: {inputs}")
            lines.append("Please specify the calculation type.")

        lines.append(f"\n⚠️ Always verify with qualified engineer for production use.")
        return "\n".join(lines)

    def is_valid_domain(self, domain: str) -> bool:
        """Check if domain exists."""
        return self._resolve_domain(domain) is not None

    def _resolve_domain(self, name: str) -> dict[str, Any] | None:
        """Resolve domain name or code to domain info."""
        name_lower = name.lower().strip()
        if name_lower in self.DOMAINS:
            return self.DOMAINS[name_lower]
        for k, v in self.DOMAINS.items():
            if name_lower in k or name_lower in v["name"].lower():
                return v
        return None


if __name__ == "__main__":
    pa = ProfessionalAssist()
    print(pa.get_help("software_eng", "How to design a REST API?"))
    print("\n---\n", pa.code_assist("python", "Build a web scraper"))
