# gnost/languages/java.py

import re
from typing import List, Optional

from gnost.languages.base import LanguageAdapter, EntryPoint, ImportEdge
from gnost.languages.manifests import find_manifests, read_text


class JavaAdapter(LanguageAdapter):
    name = "java"
    extensions = [".java"]

    # -------------------------
    # Entry Points
    # -------------------------

    def detect_entry_points(self, files: List[str]) -> List[EntryPoint]:
        entry_points: List[EntryPoint] = []

        for file in files:
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            # public static void main
            if re.search(
                r"public\s+static\s+void\s+main\s*\(\s*String",
                content,
            ):
                entry_points.append(
                    EntryPoint(file=file, reason="public static void main")
                )

            # Spring Boot entry
            if "@SpringBootApplication" in content:
                entry_points.append(
                    EntryPoint(file=file, reason="@SpringBootApplication")
                )

            # CommandLineRunner
            if "implements CommandLineRunner" in content:
                entry_points.append(EntryPoint(file=file, reason="CommandLineRunner"))

        return entry_points

    # -------------------------
    # Imports
    # -------------------------

    def detect_imports(self, file_path: str, content: str) -> List[ImportEdge]:
        imports: List[ImportEdge] = []

        for match in re.findall(
            r"^\s*import\s+([\w\.]+);",
            content,
            re.MULTILINE,
        ):
            imports.append(ImportEdge(source=file_path, target=match))

        return imports

    # -------------------------
    # Framework Detection
    # -------------------------

    # (marker found in pom.xml / build.gradle, label), strongest first.
    BUILD_FILE_MARKERS = [
        ("spring-boot", "Spring Boot"),
        ("org.springframework", "Spring Framework"),
        ("io.quarkus", "Quarkus"),
        ("io.micronaut", "Micronaut"),
        ("com.android.", "Android"),
    ]
    BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts"}

    def detect_framework_from_manifest(self, root: str) -> Optional[str]:
        labels: List[str] = []
        for path in find_manifests(root, lambda name: name in self.BUILD_FILES):
            text = read_text(path)
            for marker, label in self.BUILD_FILE_MARKERS:
                if marker in text:
                    if label not in labels:
                        labels.append(label)
                    break
        return ", ".join(labels) or None

    def detect_framework(self, files: List[str]) -> Optional[str]:
        for file in files:
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            if "@SpringBootApplication" in content:
                return "Spring Boot"

            if "org.springframework" in content:
                return "Spring Framework"

        return "Plain Java"
