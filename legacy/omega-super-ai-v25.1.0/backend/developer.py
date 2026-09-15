"""
Luqi AI Developer Workspace
============================
Expert-level developer workspace module supporting 25+ programming languages,
20+ major frameworks, code generation, review, debugging, architecture design,
and project scaffolding.

Usage:
    from backend.developer import (
        generate_code, review_code, debug_code,
        design_architecture, scaffold_project,
        explain_code, convert_code, generate_tests,
        get_languages, get_frameworks, get_methodologies,
        get_language_info,
    )
"""

from __future__ import annotations

import random
import re
import textwrap
from typing import Any

# =============================================================================
# LANGUAGE DATABASE (25 Languages)
# =============================================================================

LANGUAGE_DB: dict[str, dict[str, Any]] = {
    "python": {
        "name": "Python",
        "extension": "py",
        "comment_syntax": "#",
        "file_extension": ".py",
        "boilerplate": '''def main() -> None:
    """Entry point."""
    print("Hello, World!")

if __name__ == "__main__":
    main()
''',
        "best_practices": [
            "Follow PEP 8 style guide",
            "Use type hints for function signatures",
            "Write docstrings for all public modules, functions, classes",
            "Use list/dict comprehensions where readable",
            "Prefer f-strings for formatting",
            "Handle exceptions with specific except blocks",
            "Use virtual environments for dependency isolation",
            "Format with black / lint with ruff",
        ],
        "common_frameworks": ["django", "fastapi", "flask", "sqlalchemy", "pandas", "numpy"],
    },
    "javascript": {
        "name": "JavaScript",
        "extension": "js",
        "comment_syntax": "//",
        "file_extension": ".js",
        "boilerplate": '''console.log("Hello, World!");
''',
        "best_practices": [
            "Use const / let, avoid var",
            "Prefer async/await over callbacks",
            "Use template literals for string interpolation",
            "Write pure functions when possible",
            "Use destructuring for cleaner code",
            "Lint with ESLint, format with Prettier",
            "Add JSDoc comments for public APIs",
        ],
        "common_frameworks": ["react", "vue", "angular", "nextjs", "express", "svelte"],
    },
    "typescript": {
        "name": "TypeScript",
        "extension": "ts",
        "comment_syntax": "//",
        "file_extension": ".ts",
        "boilerplate": '''const greeting: string = "Hello, World!";
console.log(greeting);
''',
        "best_practices": [
            "Enable strict mode in tsconfig.json",
            "Use explicit return types on public APIs",
            "Prefer interfaces over types for object shapes",
            "Avoid using any; use unknown when type is uncertain",
            "Use utility types (Partial, Pick, Omit) for DRY code",
            "Organize imports and use path aliases",
        ],
        "common_frameworks": ["react", "angular", "nextjs", "nestjs", "express", "svelte"],
    },
    "java": {
        "name": "Java",
        "extension": "java",
        "comment_syntax": "//",
        "file_extension": ".java",
        "boilerplate": '''public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
''',
        "best_practices": [
            "Follow Java naming conventions (CamelCase for classes, camelCase for methods)",
            "Use meaningful variable names",
            "Prefer composition over inheritance",
            "Handle exceptions with try-catch-finally",
            "Use Streams and Optional for functional style",
            "Write unit tests with JUnit",
            "Use dependency injection frameworks like Spring",
        ],
        "common_frameworks": ["spring", "hibernate", "maven", "gradle", "junit", "mockito"],
    },
    "cpp": {
        "name": "C++",
        "extension": "cpp",
        "comment_syntax": "//",
        "file_extension": ".cpp",
        "boilerplate": '''#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
''',
        "best_practices": [
            "Use smart pointers (unique_ptr, shared_ptr) over raw pointers",
            "Follow RAII (Resource Acquisition Is Initialization)",
            "Prefer std::vector over C-style arrays",
            "Use const correctness",
            "Avoid macros; use constexpr and inline functions",
            "Write exception-safe code",
            "Use modern C++ (C++17/20) features",
        ],
        "common_frameworks": ["qt", "boost", "opencv", "sdl", "unreal", "cocos2d"],
    },
    "c": {
        "name": "C",
        "extension": "c",
        "comment_syntax": "//",
        "file_extension": ".c",
        "boilerplate": '''#include <stdio.h>

int main(void) {
    printf("Hello, World!\\n");
    return 0;
}
''',
        "best_practices": [
            "Check return values of all system calls",
            "Free all allocated memory to prevent leaks",
            "Use const for read-only data",
            "Prefer stack allocation when possible",
            "Use static analyzers (clang-static-analyzer, cppcheck)",
            "Write modular, reusable functions",
        ],
        "common_frameworks": ["gtk", "ncurses", "libuv", "openssl", "curl", "sqlite"],
    },
    "csharp": {
        "name": "C#",
        "extension": "cs",
        "comment_syntax": "//",
        "file_extension": ".cs",
        "boilerplate": '''using System;

class Program {
    static void Main(string[] args) {
        Console.WriteLine("Hello, World!");
    }
}
''',
        "best_practices": [
            "Use async/await for asynchronous operations",
            "Leverage LINQ for data manipulation",
            "Use nullable reference types when available",
            "Follow .NET naming conventions (PascalCase for methods)",
            "Implement IDisposable for unmanaged resources",
            "Use dependency injection with built-in container",
        ],
        "common_frameworks": ["dotnet", "aspnet", "xamarin", "unity", "efcore", "nunit"],
    },
    "go": {
        "name": "Go",
        "extension": "go",
        "comment_syntax": "//",
        "file_extension": ".go",
        "boilerplate": '''package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
''',
        "best_practices": [
            "Format with gofmt before committing",
            "Use go vet and staticcheck for analysis",
            "Handle errors explicitly; do not ignore them",
            "Use interfaces for testability",
            "Prefer composition over inheritance",
            "Use goroutines and channels for concurrency",
            "Write table-driven tests",
        ],
        "common_frameworks": ["gin", "echo", "gorm", "cobra", "viper", "testify"],
    },
    "rust": {
        "name": "Rust",
        "extension": "rs",
        "comment_syntax": "//",
        "file_extension": ".rs",
        "boilerplate": '''fn main() {
    println!("Hello, World!");
}
''',
        "best_practices": [
            "Embrace the ownership model; let the borrow checker help",
            "Use Result and Option for error handling",
            "Write unsafe code only when absolutely necessary",
            "Leverage pattern matching with match",
            "Use cargo clippy for linting",
            "Write unit tests with #[test] and integration tests",
        ],
        "common_frameworks": ["actix", "rocket", "axum", "tokio", "serde", "diesel"],
    },
    "ruby": {
        "name": "Ruby",
        "extension": "rb",
        "comment_syntax": "#",
        "file_extension": ".rb",
        "boilerplate": '''puts "Hello, World!"
''',
        "best_practices": [
            "Follow Ruby style guide ( RuboCop )",
            "Use meaningful names (snake_case for methods/variables)",
            "Prefer Enumerable methods over loops",
            "Write self-documenting code with clear intent",
            "Use blocks, procs, and lambdas effectively",
            "Write tests with RSpec or Minitest",
        ],
        "common_frameworks": ["rails", "sinatra", "rspec", "sidekiq", "devise", "puma"],
    },
    "php": {
        "name": "PHP",
        "extension": "php",
        "comment_syntax": "//",
        "file_extension": ".php",
        "boilerplate": '''<?php
echo "Hello, World!";
''',
        "best_practices": [
            "Use Composer for dependency management",
            "Follow PSR standards (PSR-1, PSR-2, PSR-4)",
            "Use type declarations for function parameters and return types",
            "Prefer PDO over mysql_* functions for database access",
            "Use prepared statements to prevent SQL injection",
            "Enable strict_types=1",
        ],
        "common_frameworks": ["laravel", "symfony", "wordpress", "composer", "phpunit", "eloquent"],
    },
    "swift": {
        "name": "Swift",
        "extension": "swift",
        "comment_syntax": "//",
        "file_extension": ".swift",
        "boilerplate": '''import Foundation

print("Hello, World!")
''',
        "best_practices": [
            "Use let for constants, var only when mutation is needed",
            "Prefer value types (structs) over reference types (classes)",
            "Use Optionals safely with guard let and if let",
            "Follow Swift API Design Guidelines",
            "Use protocols and protocol extensions",
            "Leverage Codable for JSON serialization",
        ],
        "common_frameworks": ["swiftui", "uikit", "alamofire", "coredata", "combine", "vapor"],
    },
    "kotlin": {
        "name": "Kotlin",
        "extension": "kt",
        "comment_syntax": "//",
        "file_extension": ".kt",
        "boilerplate": '''fun main() {
    println("Hello, World!")
}
''',
        "best_practices": [
            "Prefer val over var for immutability",
            "Use data classes for DTOs",
            "Leverage extension functions",
            "Use coroutines for asynchronous programming",
            "Apply null safety features (?, !!, ?:)",
            "Use sealed classes for representing restricted hierarchies",
        ],
        "common_frameworks": ["spring", "ktor", "android", "gradle", "kotlinx-coroutines", "exposed"],
    },
    "dart": {
        "name": "Dart",
        "extension": "dart",
        "comment_syntax": "//",
        "file_extension": ".dart",
        "boilerplate": '''void main() {
    print('Hello, World!');
}
''',
        "best_practices": [
            "Use const constructors where possible for performance",
            "Follow Effective Dart style guide",
            "Use null safety features",
            "Prefer named parameters for clarity",
            "Use streams and Future for async operations",
            "Write widget tests for Flutter apps",
        ],
        "common_frameworks": ["flutter", "angular-dart", "shelf", "bloc", "provider", "riverpod"],
    },
    "scala": {
        "name": "Scala",
        "extension": "scala",
        "comment_syntax": "//",
        "file_extension": ".scala",
        "boilerplate": '''object HelloWorld {
    def main(args: Array[String]): Unit = {
        println("Hello, World!")
    }
}
''',
        "best_practices": [
            "Prefer immutability (val over var, immutable collections)",
            "Use case classes for data modeling",
            "Leverage pattern matching",
            "Write pure functions and avoid side effects",
            "Use Option instead of null",
            "Use for-comprehensions for monadic operations",
        ],
        "common_frameworks": ["akka", "play", "spark", "http4s", "cats", "scalatest"],
    },
    "r": {
        "name": "R",
        "extension": "r",
        "comment_syntax": "#",
        "file_extension": ".R",
        "boilerplate": '''print("Hello, World!")
''',
        "best_practices": [
            "Use vectorized operations instead of loops",
            "Follow tidyverse style guide (google-r-style)",
            "Write functions to avoid code duplication",
            "Use Roxygen2 for documentation",
            "Version control with renv or packrat",
            "Use data frames/tibbles consistently",
        ],
        "common_frameworks": ["shiny", "ggplot2", "dplyr", "tidyr", "caret", "rmarkdown"],
    },
    "sql": {
        "name": "SQL",
        "extension": "sql",
        "comment_syntax": "--",
        "file_extension": ".sql",
        "boilerplate": '''SELECT 'Hello, World!' AS greeting;
''',
        "best_practices": [
            "Use consistent naming conventions",
            "Index frequently queried columns",
            "Use JOINs instead of subqueries where possible",
            "Avoid SELECT * in production queries",
            "Use transactions for multi-statement operations",
            "Parameterize queries to prevent SQL injection",
        ],
        "common_frameworks": ["postgresql", "mysql", "sqlite", "mssql", "oracle", "redshift"],
    },
    "bash": {
        "name": "Bash",
        "extension": "sh",
        "comment_syntax": "#",
        "file_extension": ".sh",
        "boilerplate": '''#!/bin/bash
echo "Hello, World!"
''',
        "best_practices": [
            "Always use set -euo pipefail at the top",
            "Quote all variable expansions",
            "Use functions to organize code",
            "Add shellcheck directives for linting",
            "Provide usage/help text",
            "Use meaningful variable names in UPPER_CASE",
        ],
        "common_frameworks": ["bash-it", "oh-my-bash", "gnu-utils", "awk", "sed", "grep"],
    },
    "powershell": {
        "name": "PowerShell",
        "extension": "ps1",
        "comment_syntax": "#",
        "file_extension": ".ps1",
        "boilerplate": '''Write-Output "Hello, World!"
''',
        "best_practices": [
            "Use approved PowerShell verbs for functions",
            "Leverage pipeline for object manipulation",
            "Use try/catch/finally for error handling",
            "Write comment-based help for functions",
            "Use PSScriptAnalyzer for linting",
            "Prefer native PowerShell cmdlets over aliases",
        ],
        "common_frameworks": ["posh-git", "oh-my-posh", "pester", "psake", "platyps", "dbatools"],
    },
    "html": {
        "name": "HTML",
        "extension": "html",
        "comment_syntax": "<!-- -->",
        "file_extension": ".html",
        "boilerplate": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World</title>
</head>
<body>
    <h1>Hello, World!</h1>
</body>
</html>
''',
        "best_practices": [
            "Use semantic HTML5 elements (header, nav, main, article, footer)",
            "Include alt text for all images",
            "Ensure accessibility with ARIA attributes",
            "Use proper document structure with DOCTYPE",
            "Validate markup with W3C validator",
            "Optimize for SEO with meta tags",
        ],
        "common_frameworks": ["bootstrap", "tailwind", "bulma", "foundation", "semantic-ui", "materialize"],
    },
    "css": {
        "name": "CSS",
        "extension": "css",
        "comment_syntax": "/* */",
        "file_extension": ".css",
        "boilerplate": '''body {
    font-family: Arial, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    margin: 0;
}

h1 {
    color: #333;
}
''',
        "best_practices": [
            "Use CSS custom properties (variables) for theming",
            "Follow BEM or utility-first naming conventions",
            "Use Flexbox and Grid for layouts",
            "Minimize specificity conflicts",
            "Use rem/em for scalable units",
            "Organize styles with @layer or methodology like ITCSS",
        ],
        "common_frameworks": ["tailwind", "bootstrap", "sass", "less", "styled-components", "postcss"],
    },
    "json": {
        "name": "JSON",
        "extension": "json",
        "comment_syntax": "N/A",
        "file_extension": ".json",
        "boilerplate": '''{
    "message": "Hello, World!"
}
''',
        "best_practices": [
            "Always use double quotes for keys and strings",
            "Validate JSON before parsing",
            "Use consistent indentation (2 or 4 spaces)",
            "Include a schema reference when applicable",
            "Keep files under 1MB for performance",
        ],
        "common_frameworks": ["json-schema", "json5", "bson", "openapi", "swagger", "graphql"],
    },
    "yaml": {
        "name": "YAML",
        "extension": "yaml",
        "comment_syntax": "#",
        "file_extension": ".yaml",
        "boilerplate": '''message: "Hello, World!"
''',
        "best_practices": [
            "Use consistent indentation (spaces, not tabs)",
            "Quote strings that contain special characters",
            "Use anchors (&) and aliases (*) for DRY config",
            "Validate YAML with a linter",
            "Avoid complex nested structures when possible",
        ],
        "common_frameworks": ["docker-compose", "kubernetes", "ansible", "github-actions", "helm", "openapi"],
    },
    "markdown": {
        "name": "Markdown",
        "extension": "md",
        "comment_syntax": "<!-- -->",
        "file_extension": ".md",
        "boilerplate": '''# Hello, World!

Welcome to your new project.
''',
        "best_practices": [
            "Use ATX-style headers (#) consistently",
            "Include a table of contents for long docs",
            "Use code fences with language identifiers",
            "Add alt text to images",
            "Use reference-style links for readability",
            "Follow a style guide (e.g., Google Markdown Style)",
        ],
        "common_frameworks": ["mkdocs", "docusaurus", "jekyll", "hugo", "gatsby", "vuepress"],
    },
    "lua": {
        "name": "Lua",
        "extension": "lua",
        "comment_syntax": "--",
        "file_extension": ".lua",
        "boilerplate": '''print("Hello, World!")
''',
        "best_practices": [
            "Use local variables by default (fast, scoped)",
            "Follow Lua style guide (indentation, naming)",
            "Use modules with require for organization",
            "Leverage metatables for OOP patterns",
            "Write unit tests with busted or luaunit",
            "Profile performance with debug library",
        ],
        "common_frameworks": ["openresty", "love2d", "torch", "luvit", "penlight", "luarocks"],
    },
}


# =============================================================================
# FRAMEWORK DATABASE (20 Frameworks)
# =============================================================================

FRAMEWORK_DB: dict[str, dict[str, Any]] = {
    "react": {
        "name": "React",
        "language": "javascript",
        "type": "web",
        "boilerplate": {
            "src/App.jsx": '''import React from 'react';

function App() {
    return (
        <div className="App">
            <h1>Hello, World!</h1>
        </div>
    );
}

export default App;
''',
            "src/main.jsx": '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);
''',
            "public/index.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>React App</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
</body>
</html>
''',
            "package.json": '''{
  "name": "react-app",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8"
  }
}
''',
        },
        "key_files": ["src/App.jsx", "src/main.jsx", "package.json", "vite.config.js"],
    },
    "vue": {
        "name": "Vue.js",
        "language": "javascript",
        "type": "web",
        "boilerplate": {
            "src/App.vue": '''<template>
  <div id="app">
    <h1>{{ message }}</h1>
  </div>
</template>

<script setup>
import { ref } from 'vue';
const message = ref('Hello, World!');
</script>

<style scoped>
h1 { color: #42b883; }
</style>
''',
            "src/main.js": '''import { createApp } from 'vue';
import App from './App.vue';

createApp(App).mount('#app');
''',
            "index.html": '''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /><title>Vue App</title></head>
<body><div id="app"></div><script type="module" src="/src/main.js"></script></body>
</html>
''',
        },
        "key_files": ["src/App.vue", "src/main.js", "index.html", "vite.config.js", "package.json"],
    },
    "angular": {
        "name": "Angular",
        "language": "typescript",
        "type": "web",
        "boilerplate": {
            "src/app/app.component.ts": '''import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: `<h1>{{ title }}</h1>`,
  styles: [`h1 { color: #dd0031; }`]
})
export class AppComponent {
  title = 'Hello, World!';
}
''',
            "src/main.ts": '''import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent).catch(err => console.error(err));
''',
        },
        "key_files": ["src/app/app.component.ts", "src/main.ts", "angular.json", "package.json"],
    },
    "nextjs": {
        "name": "Next.js",
        "language": "javascript",
        "type": "web",
        "boilerplate": {
            "app/page.js": '''export default function Home() {
    return (
        <main>
            <h1>Hello, World!</h1>
        </main>
    );
}
''',
            "app/layout.js": '''export const metadata = { title: 'Next.js App' };

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
''',
        },
        "key_files": ["app/page.js", "app/layout.js", "next.config.js", "package.json"],
    },
    "express": {
        "name": "Express.js",
        "language": "javascript",
        "type": "api",
        "boilerplate": {
            "app.js": '''const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

app.get('/', (req, res) => {
    res.json({ message: 'Hello, World!' });
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
''',
            "package.json": '''{
  "name": "express-app",
  "version": "1.0.0",
  "main": "app.js",
  "scripts": { "start": "node app.js", "dev": "nodemon app.js" },
  "dependencies": { "express": "^4.18.2" },
  "devDependencies": { "nodemon": "^3.0.1" }
}
''',
        },
        "key_files": ["app.js", "package.json", "routes/index.js", "middleware/logger.js"],
    },
    "django": {
        "name": "Django",
        "language": "python",
        "type": "web",
        "boilerplate": {
            "manage.py": '''#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
''',
            "config/settings.py": '''from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-dev-key-change-me'
DEBUG = True
ALLOWED_HOSTS = []
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth',
    'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles',
    'core',
]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
''',
            "core/views.py": '''from django.http import JsonResponse

def hello(request):
    return JsonResponse({"message": "Hello, World!"})
''',
            "core/urls.py": '''from django.urls import path
from . import views

urlpatterns = [
    path('', views.hello, name='hello'),
]
''',
        },
        "key_files": ["manage.py", "config/settings.py", "core/views.py", "core/urls.py", "requirements.txt"],
    },
    "fastapi": {
        "name": "FastAPI",
        "language": "python",
        "type": "api",
        "boilerplate": {
            "main.py": '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="My API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
''',
            "requirements.txt": '''fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
''',
        },
        "key_files": ["main.py", "requirements.txt", "Dockerfile", "docker-compose.yml"],
    },
    "flask": {
        "name": "Flask",
        "language": "python",
        "type": "web",
        "boilerplate": {
            "app.py": '''from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def hello():
    return jsonify({"message": "Hello, World!"})

if __name__ == "__main__":
    app.run(debug=True)
''',
            "requirements.txt": '''flask>=3.0.0
''',
        },
        "key_files": ["app.py", "requirements.txt", "templates/index.html", "static/style.css"],
    },
    "spring": {
        "name": "Spring Boot",
        "language": "java",
        "type": "api",
        "boilerplate": {
            "src/main/java/com/example/demo/DemoApplication.java": '''package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
''',
            "src/main/java/com/example/demo/HelloController.java": '''package com.example.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    @GetMapping("/")
    public String hello() {
        return "Hello, World!";
    }
}
''',
            "pom.xml": '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0</version>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>
    <dependencies>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
    </dependencies>
</project>
''',
        },
        "key_files": ["pom.xml", "src/main/java/com/example/demo/DemoApplication.java", "src/main/resources/application.properties"],
    },
    "laravel": {
        "name": "Laravel",
        "language": "php",
        "type": "web",
        "boilerplate": {
            "routes/web.php": '''<?php

use Illuminate\\Support\\Facades\\Route;

Route::get('/', function () {
    return view('welcome');
});
''',
        },
        "key_files": ["routes/web.php", "routes/api.php", "composer.json", ".env.example", "artisan"],
    },
    "rails": {
        "name": "Ruby on Rails",
        "language": "ruby",
        "type": "web",
        "boilerplate": {
            "app/controllers/application_controller.rb": '''class ApplicationController < ActionController::Base
end
''',
            "config/routes.rb": '''Rails.application.routes.draw do
    root "application#index"
end
''',
            "Gemfile": '''source "https://rubygems.org"
gem "rails", "~> 7.1"
gem "sqlite3", "~> 1.4"
gem "puma", ">= 5.0"
''',
        },
        "key_files": ["Gemfile", "config/routes.rb", "app/controllers", "config/application.rb"],
    },
    "flutter": {
        "name": "Flutter",
        "language": "dart",
        "type": "mobile",
        "boilerplate": {
            "lib/main.dart": '''import 'package:flutter/material.dart';

void main() {
    runApp(const MyApp());
}

class MyApp extends StatelessWidget {
    const MyApp({super.key});

    @override
    Widget build(BuildContext context) {
        return MaterialApp(
            title: 'Flutter Demo',
            theme: ThemeData(primarySwatch: Colors.blue),
            home: const MyHomePage(),
        );
    }
}

class MyHomePage extends StatelessWidget {
    const MyHomePage({super.key});

    @override
    Widget build(BuildContext context) {
        return Scaffold(
            appBar: AppBar(title: const Text('Home')),
            body: const Center(child: Text('Hello, World!')),
        );
    }
}
''',
            "pubspec.yaml": '''name: flutter_app
description: A new Flutter project.
publish_to: 'none'
version: 1.0.0+1
environment:
    sdk: '>=3.0.0 <4.0.0'
dependencies:
    flutter:
        sdk: flutter
dev_dependencies:
    flutter_test:
        sdk: flutter
    flutter_lints: ^3.0.0
flutter:
    uses-material-design: true
''',
        },
        "key_files": ["lib/main.dart", "pubspec.yaml", "android/build.gradle", "ios/Runner/AppDelegate.swift"],
    },
    "react-native": {
        "name": "React Native",
        "language": "javascript",
        "type": "mobile",
        "boilerplate": {
            "App.js": '''import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function App() {
    return (
        <View style={styles.container}>
            <Text style={styles.text}>Hello, World!</Text>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, justifyContent: 'center', alignItems: 'center' },
    text: { fontSize: 24 },
});
''',
            "package.json": '''{
  "name": "rn-app",
  "version": "1.0.0",
  "main": "node_modules/expo/AppEntry.js",
  "scripts": { "start": "expo start" },
  "dependencies": { "expo": "~49.0.0", "react": "18.2.0", "react-native": "0.72.0" }
}
''',
        },
        "key_files": ["App.js", "package.json", "app.json", "babel.config.js"],
    },
    "svelte": {
        "name": "Svelte",
        "language": "javascript",
        "type": "web",
        "boilerplate": {
            "src/App.svelte": '''<script>
    let name = 'World';
</script>

<main>
    <h1>Hello, {name}!</h1>
</main>

<style>
    h1 { color: #ff3e00; }
</style>
''',
            "src/main.js": '''import App from './App.svelte';

const app = new App({ target: document.getElementById('app') });
export default app;
''',
        },
        "key_files": ["src/App.svelte", "src/main.js", "vite.config.js", "svelte.config.js"],
    },
    "nuxtjs": {
        "name": "Nuxt.js",
        "language": "javascript",
        "type": "web",
        "boilerplate": {
            "app.vue": '''<template>
  <div>
    <NuxtPage />
  </div>
</template>
''',
            "pages/index.vue": '''<template>
  <h1>Hello, World!</h1>
</template>
''',
            "nuxt.config.ts": '''export default defineNuxtConfig({
    devtools: { enabled: true }
});
''',
        },
        "key_files": ["app.vue", "pages/index.vue", "nuxt.config.ts", "package.json"],
    },
    "gin": {
        "name": "Gin",
        "language": "go",
        "type": "api",
        "boilerplate": {
            "main.go": '''package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

func main() {
    r := gin.Default()
    r.GET("/", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{"message": "Hello, World!"})
    })
    r.Run(":8080")
}
''',
            "go.mod": '''module gin-app

go 1.21

require github.com/gin-gonic/gin v1.9.1
''',
        },
        "key_files": ["main.go", "go.mod", "go.sum", "handlers/", "middleware/"],
    },
    "actix": {
        "name": "Actix Web",
        "language": "rust",
        "type": "api",
        "boilerplate": {
            "src/main.rs": '''use actix_web::{get, App, HttpResponse, HttpServer, Responder};

#[get("/")]
async fn hello() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({"message": "Hello, World!"}))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| App::new().service(hello))
        .bind(("127.0.0.1", 8080))?
        .run()
        .await
}
''',
            "Cargo.toml": '''[package]
name = "actix-app"
version = "1.0.0"
edition = "2021"

[dependencies]
actix-web = "4"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
''',
        },
        "key_files": ["src/main.rs", "Cargo.toml", "Cargo.lock", "src/routes/", "src/models/"],
    },
    "dotnet": {
        "name": ".NET",
        "language": "csharp",
        "type": "api",
        "boilerplate": {
            "Program.cs": '''var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => new { message = "Hello, World!" });

app.Run();
''',
            "dotnet.csproj": '''<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
''',
        },
        "key_files": ["Program.cs", ".csproj", "appsettings.json", "Properties/launchSettings.json"],
    },
    "fastify": {
        "name": "Fastify",
        "language": "javascript",
        "type": "api",
        "boilerplate": {
            "app.js": '''const fastify = require('fastify')({ logger: true });

fastify.get('/', async () => {
    return { message: 'Hello, World!' };
});

const start = async () => {
    try {
        await fastify.listen({ port: 3000 });
    } catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
};
start();
''',
            "package.json": '''{
  "name": "fastify-app",
  "version": "1.0.0",
  "main": "app.js",
  "scripts": { "start": "node app.js", "dev": "nodemon app.js" },
  "dependencies": { "fastify": "^4.24.0" },
  "devDependencies": { "nodemon": "^3.0.1" }
}
''',
        },
        "key_files": ["app.js", "package.json", "plugins/", "routes/"],
    },
    "nestjs": {
        "name": "NestJS",
        "language": "typescript",
        "type": "api",
        "boilerplate": {
            "src/main.ts": '''import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
    const app = await NestFactory.create(AppModule);
    await app.listen(3000);
}
bootstrap();
''',
            "src/app.module.ts": '''import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
    imports: [],
    controllers: [AppController],
    providers: [AppService],
})
export class AppModule {}
''',
            "src/app.controller.ts": '''import { Controller, Get } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
    constructor(private readonly appService: AppService) {}

    @Get()
    getHello(): string {
        return this.appService.getHello();
    }
}
''',
            "src/app.service.ts": '''import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
    getHello(): string {
        return 'Hello, World!';
    }
}
''',
        },
        "key_files": ["src/main.ts", "src/app.module.ts", "src/app.controller.ts", "nest-cli.json", "package.json"],
    },
}


# =============================================================================
# METHODOLOGY TEMPLATES (12 Methodologies)
# =============================================================================

METHODOLOGY_DB: dict[str, dict[str, Any]] = {
    "agile": {
        "name": "Agile",
        "description": "Iterative approach delivering work in small, incremental releases with continuous feedback.",
        "phases": ["Requirements", "Design", "Development", "Testing", "Deployment", "Review"],
        "deliverables": ["Product Backlog", "Sprint Backlog", "Working Software", "Sprint Review", "Retrospective Notes"],
    },
    "scrum": {
        "name": "Scrum",
        "description": "Framework for managing iterative work through fixed-length sprints with defined roles and ceremonies.",
        "phases": ["Sprint Planning", "Daily Standup", "Development", "Sprint Review", "Sprint Retrospective"],
        "deliverables": ["Product Backlog", "Sprint Backlog", "Increment", "Burndown Chart", "Retrospective Action Items"],
    },
    "kanban": {
        "name": "Kanban",
        "description": "Visual workflow management focusing on continuous delivery without overloading the team.",
        "phases": ["Backlog", "To Do", "In Progress", "Review", "Done"],
        "deliverables": ["Kanban Board", "Cumulative Flow Diagram", "Lead Time Report", "Throughput Metrics"],
    },
    "waterfall": {
        "name": "Waterfall",
        "description": "Sequential design process where each phase cascades into the next.",
        "phases": ["Requirements", "System Design", "Implementation", "Testing", "Deployment", "Maintenance"],
        "deliverables": ["Requirements Document", "Design Specification", "Source Code", "Test Reports", "User Manual", "Maintenance Plan"],
    },
    "devops": {
        "name": "DevOps",
        "description": "Culture and practice bridging development and operations for faster, reliable delivery.",
        "phases": ["Plan", "Develop", "Build", "Test", "Release", "Deploy", "Operate", "Monitor"],
        "deliverables": ["CI/CD Pipeline", "Infrastructure as Code", "Monitoring Dashboard", "Incident Response Plan", "Automation Scripts"],
    },
    "tdd": {
        "name": "Test-Driven Development",
        "description": "Development practice writing tests before code to ensure correctness and drive design.",
        "phases": ["Write Failing Test", "Write Minimal Code", "Run Tests", "Refactor", "Repeat"],
        "deliverables": ["Test Suite", "Production Code", "Refactored Code", "Test Coverage Report"],
    },
    "bdd": {
        "name": "Behavior-Driven Development",
        "description": "Collaborative approach using natural language to define application behavior.",
        "phases": ["Discovery", "Formulation", "Automation", "Implementation", "Validation"],
        "deliverables": ["Feature Files (Gherkin)", "Step Definitions", "Living Documentation", "Executable Specifications"],
    },
    "lean": {
        "name": "Lean",
        "description": "Methodology focused on minimizing waste and maximizing value delivery.",
        "phases": ["Identify Value", "Map Value Stream", "Create Flow", "Establish Pull", "Seek Perfection"],
        "deliverables": ["Value Stream Map", "MVP", "Kanban Board", "Metrics Dashboard", "Improvement Plan"],
    },
    "xp": {
        "name": "Extreme Programming",
        "description": "Agile methodology emphasizing technical excellence and customer satisfaction.",
        "phases": ["Planning", "Design", "Coding", "Testing", "Listening", "Refactoring"],
        "deliverables": ["User Stories", "Test Suite", "Working Code", "Refactored Code", "Iteration Plan"],
    },
    "spiral": {
        "name": "Spiral Model",
        "description": "Risk-driven process model combining iterative development with systematic risk analysis.",
        "phases": ["Planning", "Risk Analysis", "Engineering", "Evaluation"],
        "deliverables": ["Risk Assessment", "Prototype", "Requirements Document", "Design Document", "Working Software"],
    },
    "v-model": {
        "name": "V-Model",
        "description": "Extension of Waterfall where each development phase has a corresponding testing phase.",
        "phases": ["Requirements Analysis", "System Design", "Architecture Design", "Module Design", "Coding", "Unit Testing", "Integration Testing", "System Testing", "Acceptance Testing"],
        "deliverables": ["Requirements Spec", "System Test Plan", "Architecture Design", "Integration Test Plan", "Module Design", "Unit Tests", "Test Reports", "User Acceptance Report"],
    },
    "rad": {
        "name": "Rapid Application Development",
        "description": "Iterative approach emphasizing rapid prototyping and user feedback over strict planning.",
        "phases": ["Requirements Planning", "User Design", "Construction", "Cutover"],
        "deliverables": ["Requirements Outline", "Working Prototype", "Production Application", "User Training", "Deployment Plan"],
    },
}


# =============================================================================
# GITIGNORE TEMPLATES
# =============================================================================

GITIGNORE_TEMPLATES: dict[str, str] = {
    "python": '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db
''',
    "javascript": '''# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
package-lock.json
yarn.lock
pnpm-lock.yaml

# Build
dist/
build/
.out/
.next/
.nuxt/

# IDEs
.vscode/
.idea/
*.swp

# Environment
.env
.env.local
.env.*.local

# Testing
coverage/
*.lcov

# OS
.DS_Store
Thumbs.db
''',
    "typescript": '''# Dependencies
node_modules/
npm-debug.log*
yarn-error.log*
package-lock.json
yarn.lock

# Build
dist/
build/
*.tsbuildinfo

# IDEs
.vscode/
.idea/
*.swp

# Environment
.env
.env.local

# Testing
coverage/

# OS
.DS_Store
Thumbs.db
''',
    "java": '''# Compiled
*.class
*.jar
*.war
*.ear
target/
build/

# IDEs
.idea/
*.iml
*.ipr
*.iws
.classpath
.project
.settings/
vscode/

# Gradle
.gradle/
!gradle-wrapper.jar

# Maven
pom.xml.tag
pom.xml.releaseBackup

# OS
.DS_Store
Thumbs.db
''',
    "go": '''# Binaries
*.exe
*.exe~
*.dll
*.so
*.dylib
bin/

# Test
*.test
*.out
coverage.html
coverage.out

# Dependencies
vendor/

# IDEs
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
''',
    "rust": '''# Build
target/
Cargo.lock

# IDEs
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
''',
    "csharp": '''# Build
bin/
obj/
out/

# IDEs
.vs/
.idea/
*.user
*.suo

# NuGet
*.nupkg

# OS
.DS_Store
Thumbs.db
''',
    "ruby": '''# Bundler
/.bundle/
/vendor/bundle

# Build
pkg/

# IDEs
.idea/
.vscode/
*.swp

# Testing
coverage/

# OS
.DS_Store
Thumbs.db
''',
    "php": '''# Composer
/vendor/
composer.lock

# IDEs
.idea/
.vscode/
*.swp

# Environment
.env

# OS
.DS_Store
Thumbs.db
''',
    "dart": '''# Flutter/Dart
.dart_tool/
.flutter-plugins
.packages
build/
pubspec.lock

# IDEs
.idea/
.vscode/

# OS
.DS_Store
Thumbs.db
''',
    "swift": '''# Xcode
build/
DerivedData/
*.xcworkspace
*.xcuserdata
*.xccheckout

# Swift Package Manager
.build/
Package.resolved

# IDEs
.idea/
.vscode/

# OS
.DS_Store
''',
    "kotlin": '''# Gradle
.gradle/
build/

# IDEs
.idea/
*.iml

# OS
.DS_Store
Thumbs.db
''',
    "cpp": '''# Compiled
*.o
*.obj
*.exe
*.out
*.a
*.so
*.dll
build/
cmake-build-*/

# IDEs
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
''',
    "c": '''# Compiled
*.o
*.obj
*.exe
*.out
*.a
*.so
*.dll
build/

# IDEs
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
''',
    "scala": '''# SBT
target/
project/target/
.bsp/

# IDEs
.idea/
*.iml
.vscode/
.metals/

# OS
.DS_Store
Thumbs.db
''',
    "default": '''# IDEs
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db
''',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_gitignore(language: str) -> str:
    """Return the .gitignore template for a given language."""
    return GITIGNORE_TEMPLATES.get(language, GITIGNORE_TEMPLATES["default"])


def _safe_filename(name: str) -> str:
    """Convert a project name to a safe directory name."""
    return re.sub(r"[^a-zA-Z0_\-]", "_", name.lower())


def _build_file_tree(files: list[dict[str, str]]) -> dict:
    """Convert a flat file list into a nested tree structure."""
    tree: dict[str, Any] = {}
    for f in files:
        parts = f["path"].split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None
    return tree


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def generate_code(
    prompt: str,
    language: str,
    framework: str = "",
    context: str = "",
) -> dict[str, Any]:
    """
    Generate a structured prompt for code generation.

    The caller (router) should send the returned ``prompt`` to an LLM (OpenAI).

    Parameters
    ----------
    prompt : str
        Natural-language description of what to build.
    language : str
        Target programming language key (e.g. ``"python"``).
    framework : str, optional
        Framework key (e.g. ``"fastapi"``).
    context : str, optional
        Additional domain context or constraints.

    Returns
    -------
    dict
        ``{"code", "language", "explanation", "file_name", "prompt", "system"}``
    """
    lang_info = LANGUAGE_DB.get(language, {})
    lang_name = lang_info.get("name", language)
    ext = lang_info.get("extension", language)
    fw_info = FRAMEWORK_DB.get(framework, {}) if framework else {}
    fw_name = fw_info.get("name", framework) if framework else ""

    system_msg = (
        f"You are an expert {lang_name} developer"
        + (f" specializing in {fw_name}" if fw_name else "")
        + ". Write clean, well-documented, production-ready code."
    )

    user_prompt = f"""Language: {lang_name}
{("Framework: " + fw_name) if fw_name else ""}
{("Context: " + context) if context else ""}

Task: {prompt}

Please provide ONLY the code and a brief explanation. The code should follow best practices for {lang_name}.
"""

    file_name = f"generated_{random.randint(1000, 9999)}.{ext}"

    return {
        "code": "",
        "language": lang_name,
        "explanation": "",
        "file_name": file_name,
        "prompt": user_prompt.strip(),
        "system": system_msg,
    }


def review_code(code: str, language: str) -> dict[str, Any]:
    """
    Build a structured prompt for code review.

    Parameters
    ----------
    code : str
        Source code to review.
    language : str
        Programming language key.

    Returns
    -------
    dict
        ``{"score", "issues", "suggestions", "improved_code", "prompt", "system"}``
    """
    lang_info = LANGUAGE_DB.get(language, {})
    lang_name = lang_info.get("name", language)
    best_practices = lang_info.get("best_practices", [])

    system_msg = (
        f"You are a senior {lang_name} code reviewer. "
        "Analyze the code for bugs, security issues, performance, style, and maintainability."
    )

    practices_section = ""
    if best_practices:
        practices_section = "\\nBest practices for this language:\\n" + "\\n".join(
            f"- {p}" for p in best_practices[:5]
        )

    prompt = f"""Review the following {lang_name} code:

```{language}
{code}
```
{practices_section}

Please provide:
1. A quality score from 0-100
2. A list of specific issues found
3. Actionable suggestions for improvement
4. The improved version of the code
"""

    return {
        "score": 0,
        "issues": [],
        "suggestions": [],
        "improved_code": "",
        "prompt": prompt.strip(),
        "system": system_msg,
    }


def debug_code(code: str, error: str, language: str) -> dict[str, Any]:
    """
    Build a structured prompt for debugging code.

    Parameters
    ----------
    code : str
        The code that is failing.
    error : str
        Error message or description of the problem.
    language : str
        Programming language key.

    Returns
    -------
    dict
        ``{"diagnosis", "fix", "explanation", "prompt", "system"}``
    """
    lang_info = LANGUAGE_DB.get(language, {})
    lang_name = lang_info.get("name", language)

    system_msg = (
        f"You are an expert {lang_name} debugger. "
        "Diagnose issues accurately and provide precise fixes with clear explanations."
    )

    prompt = f"""Debug the following {lang_name} code.

Error/Problem:
{error}

Code:
```{language}
{code}
```

Please provide:
1. A clear diagnosis of the root cause
2. The fixed code
3. A brief explanation of what was wrong and how the fix resolves it
"""

    return {
        "diagnosis": "",
        "fix": "",
        "explanation": "",
        "prompt": prompt.strip(),
        "system": system_msg,
    }


def design_architecture(description: str, scale: str = "medium") -> dict[str, Any]:
    """
    Build a structured prompt for system architecture design.

    Parameters
    ----------
    description : str
        Description of the system to design.
    scale : str
        Scale of the system: ``"small"``, ``"medium"``, or ``"large"``.

    Returns
    -------
    dict
        ``{"diagram_text", "components", "tech_stack", "data_flow", "prompt", "system"}``
    """
    system_msg = (
        "You are a principal software architect with 20 years of experience. "
        "Design scalable, maintainable, production-ready system architectures."
    )

    scale_guidance = {
        "small": "Design a simple, cost-effective architecture suitable for a startup or MVP.",
        "medium": "Design a scalable architecture with room for growth, including caching and monitoring.",
        "large": "Design an enterprise-grade, highly available architecture with microservices, event-driven patterns, and disaster recovery.",
    }.get(scale, "Design a scalable architecture with room for growth.")

    prompt = f"""Design a system architecture for the following requirements:

Description:
{description}

Scale: {scale}
{scale_guidance}

Please provide:
1. An ASCII/text-based architecture diagram
2. A list of key components with their responsibilities
3. A recommended tech stack with justification
4. A description of the data flow between components
"""

    return {
        "diagram_text": "",
        "components": [],
        "tech_stack": [],
        "data_flow": "",
        "prompt": prompt.strip(),
        "system": system_msg,
    }


def scaffold_project(
    name: str,
    project_type: str,
    language: str,
    framework: str = "",
    features: list[str] | None = None,
) -> dict[str, Any]:
    """
    Generate a complete project scaffold with real boilerplate code.

    Parameters
    ----------
    name : str
        Project name.
    project_type : str
        Type of project: ``"webapp"``, ``"api"``, ``"cli"``, ``"library"``, ``"mobile"``.
    language : str
        Primary programming language key.
    framework : str, optional
        Framework key (e.g. ``"fastapi"``, ``"react"``).
    features : list[str], optional
        Additional features to include (e.g. ``["auth", "db", "docker"]``).

    Returns
    -------
    dict
        ``{"files": [{"path", "content"}], "structure", "setup_commands"}``
    """
    features = features or []
    safe_name = _safe_filename(name)
    lang_info = LANGUAGE_DB.get(language, {})
    lang_name = lang_info.get("name", language)
    ext = lang_info.get("extension", language)
    fw_info = FRAMEWORK_DB.get(framework, {}) if framework else {}
    fw_boilerplate = fw_info.get("boilerplate", {}) if fw_info else {}

    files: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # 1. Framework boilerplate files (if framework is specified)
    # ------------------------------------------------------------------
    if fw_boilerplate:
        for file_path, content in fw_boilerplate.items():
            files.append({"path": file_path, "content": content})

    # ------------------------------------------------------------------
    # 2. Language-specific .gitignore
    # ------------------------------------------------------------------
    files.append({"path": ".gitignore", "content": _get_gitignore(language)})

    # ------------------------------------------------------------------
    # 3. README.md
    # ------------------------------------------------------------------
    features_list = "\\n".join(f"- {f.title()}" for f in features) if features else "- Core functionality"

    readme_content = f"""# {name}

A {project_type} project built with {lang_name}{f" and {framework}" if framework else ""}.

## Getting Started

### Prerequisites

- {lang_name} installed
{f"- {framework} CLI/tooling installed" if framework else ""}

### Installation

```bash
{chr(10).join(_generate_setup_commands(language, framework, safe_name))}
```

## Project Structure

```
{_generate_tree_text(files)}
```

## Features

{features_list}

## License

MIT
"""
    files.append({"path": "README.md", "content": readme_content})

    # ------------------------------------------------------------------
    # 4. Environment / Config files
    # ------------------------------------------------------------------
    if "docker" in features:
        files.append({"path": "Dockerfile", "content": _generate_dockerfile(language, framework)})
        files.append({
            "path": "docker-compose.yml",
            "content": f"""version: '3.8'

services:
  {safe_name}:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
    volumes:
      - .:/app
""",
        })

    if "db" in features:
        files.append({
            "path": "docker-compose.yml",
            "content": f"""version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: {safe_name}
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
""",
        })

    # ------------------------------------------------------------------
    # 5. Context-aware source files (if no framework boilerplate covered them)
    # ------------------------------------------------------------------
    existing_paths = {f["path"] for f in files}

    if project_type == "webapp" and not framework:
        if "index.html" not in existing_paths:
            files.append({
                "path": "index.html",
                "content": f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>{name}</h1>
    <p>Welcome to your new project!</p>
    <script src="app.js"></script>
</body>
</html>
""",
            })
        if "style.css" not in existing_paths:
            files.append({
                "path": "style.css",
                "content": """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
}
""",
            })
        if "app.js" not in existing_paths:
            files.append({
                "path": "app.js",
                "content": """document.addEventListener('DOMContentLoaded', () => {
    console.log('App initialized!');
});
""",
            })

    elif project_type == "api" and not framework:
        if language == "python" and "main.py" not in existing_paths:
            files.append({
                "path": "main.py",
                "content": f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{name}", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {{"message": "Welcome to {name}"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}
""",
            })
        if "requirements.txt" not in existing_paths:
            files.append({
                "path": "requirements.txt",
                "content": "fastapi>=0.104.0\\nuvicorn[standard]>=0.24.0\\n",
            })
        if "config.py" not in existing_paths:
            files.append({
                "path": "config.py",
                "content": """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "My API"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./app.db"
    SECRET_KEY: str = "change-me"

    class Config:
        env_file = ".env"

settings = Settings()
""",
            })

    elif project_type == "cli":
        if language == "python" and f"main.{ext}" not in existing_paths:
            files.append({
                "path": f"{safe_name}/__init__.py",
                "content": "",
            })
            files.append({
                "path": f"{safe_name}/cli.py",
                "content": f"""import argparse


def main():
    parser = argparse.ArgumentParser(description="{name} CLI")
    parser.add_argument("--version", action="version", version="1.0.0")
    parser.add_argument("input", help="Input file or data")
    args = parser.parse_args()
    print(f"Processing: {{args.input}}")


if __name__ == "__main__":
    main()
""",
            })
            files.append({
                "path": "setup.py",
                "content": f"""from setuptools import setup, find_packages

setup(
    name="{safe_name}",
    version="1.0.0",
    packages=find_packages(),
    entry_points={{
        "console_scripts": [
            "{safe_name}={safe_name}.cli:main",
        ],
    }},
)
""",
            })

    elif project_type == "library":
        if language == "python":
            files.append({"path": f"{safe_name}/__init__.py", "content": f'"""{name} - A Python library."""\\n\\n__version__ = "1.0.0"\\n'})
            files.append({
                "path": f"{safe_name}/core.py",
                "content": f"""\"\"\"Core module for {name}.\"\"\"


def hello() -> str:
    \"\"\"Return a greeting.\"\"\"
    return "Hello from {name}!"
""",
            })
            files.append({
                "path": "tests/__init__.py",
                "content": "",
            })
            files.append({
                "path": "tests/test_core.py",
                "content": f"""import pytest
from {safe_name}.core import hello


def test_hello():
    assert hello() == "Hello from {name}!"
""",
            })
            files.append({
                "path": "pyproject.toml",
                "content": f"""[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{safe_name}"
version = "1.0.0"
description = "A Python library"
requires-python = ">=3.9"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0", "black", "ruff"]
""",
            })

    # ------------------------------------------------------------------
    # 6. Auth feature
    # ------------------------------------------------------------------
    if "auth" in features and language == "python":
        files.append({
            "path": "auth.py",
            "content": """from datetime import datetime, timedelta
from typing import Optional

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    \"\"\"Create a JWT-like access token.\"\"\"
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    # In production, use jose JWT library
    return f"token_{{to_encode['sub']}}_{{expire.timestamp()}}"


def verify_token(token: str) -> bool:
    \"\"\"Verify an access token.\"\"\"
    # Production: decode JWT and verify signature
    return token.startswith("token_")
""",
        })

    # Build tree structure
    tree = _build_file_tree(files)
    setup_cmds = _generate_setup_commands(language, framework, safe_name)

    return {
        "files": files,
        "structure": tree,
        "setup_commands": setup_cmds,
    }


def explain_code(code: str, language: str) -> dict[str, Any]:
    """
    Build a structured prompt for code explanation.

    Parameters
    ----------
    code : str
        Source code to explain.
    language : str
        Programming language key.

    Returns
    -------
    dict
        ``{"explanation", "complexity", "key_concepts", "prompt", "system"}``
    """
    lang_info = LANGUAGE_DB.get(language, {})
    lang_name = lang_info.get("name", language)

    system_msg = (
        f"You are an expert {lang_name} educator. "
        "Explain code clearly, covering what it does, why it works, and key concepts involved."
    )

    prompt = f"""Explain the following {lang_name} code in detail:

```{language}
{code}
```

Please provide:
1. A clear, beginner-friendly explanation of what the code does
2. The time/space complexity (Big O notation)
3. A list of key programming concepts demonstrated
"""

    return {
        "explanation": "",
        "complexity": "",
        "key_concepts": [],
        "prompt": prompt.strip(),
        "system": system_msg,
    }


def convert_code(code: str, from_lang: str, to_lang: str) -> dict[str, Any]:
    """
    Build a structured prompt for code language conversion.

    Parameters
    ----------
    code : str
        Source code to convert.
    from_lang : str
        Source language key.
    to_lang : str
        Target language key.

    Returns
    -------
    dict
        ``{"code", "language", "notes", "prompt", "system"}``
    """
    from_info = LANGUAGE_DB.get(from_lang, {})
    to_info = LANGUAGE_DB.get(to_lang, {})
    from_name = from_info.get("name", from_lang)
    to_name = to_info.get("name", to_lang)
    to_ext = to_info.get("extension", to_lang)

    system_msg = (
        f"You are a polyglot developer expert in both {from_name} and {to_name}. "
        f"Translate code accurately, preserving behavior and adapting idioms."
    )

    prompt = f"""Convert the following {from_name} code to {to_name}:

```{from_lang}
{code}
```

Please provide:
1. The equivalent {to_name} code
2. Notes on any semantic differences, idiomatic changes, or caveats
"""

    return {
        "code": "",
        "language": to_name,
        "notes": "",
        "prompt": prompt.strip(),
        "system": system_msg,
    }


def generate_tests(code: str, language: str, test_type: str = "unit") -> dict[str, Any]:
    """
    Build a structured prompt for test generation.

    Parameters
    ----------
    code : str
        Source code to test.
    language : str
        Programming language key.
    test_type : str
        Type of tests: ``"unit"``, ``"integration"``, ``"e2e"``.

    Returns
    -------
    dict
        ``{"tests", "framework", "coverage_notes", "prompt", "system"}``
    """
    lang_info = LANGUAGE_DB.get(language, {})
    lang_name = lang_info.get("name", language)

    test_frameworks = {
        "python": "pytest",
        "javascript": "jest",
        "typescript": "jest",
        "java": "JUnit 5",
        "go": "testing + testify",
        "rust": "built-in test + tokio-test",
        "ruby": "RSpec",
        "php": "PHPUnit",
        "csharp": "xUnit",
        "swift": "XCTest",
        "kotlin": "JUnit 5 + MockK",
        "cpp": "Google Test",
        "c": "Unity Test Framework",
        "scala": "ScalaTest",
        "dart": "flutter_test",
    }

    framework = test_frameworks.get(language, "appropriate testing framework")

    system_msg = (
        f"You are a {lang_name} testing expert. "
        f"Write comprehensive {test_type} tests using {framework}."
    )

    prompt = f"""Generate {test_type} tests for the following {lang_name} code:

```{language}
{code}
```

Testing Framework: {framework}

Please provide:
1. Complete, runnable test code
2. Notes on test coverage and any edge cases handled
3. Any additional test fixtures or mocks needed
"""

    return {
        "tests": "",
        "framework": framework,
        "coverage_notes": "",
        "prompt": prompt.strip(),
        "system": system_msg,
    }


def get_languages() -> list[dict[str, str]]:
    """
    Return a list of all supported programming languages.

    Returns
    -------
    list[dict]
        Each dict contains ``key``, ``name``, and ``extension``.
    """
    return [
        {"key": k, "name": v["name"], "extension": v["extension"]}
        for k, v in LANGUAGE_DB.items()
    ]


def get_frameworks(language: str | None = None) -> list[dict[str, str]]:
    """
    Return a list of all frameworks, optionally filtered by language.

    Parameters
    ----------
    language : str, optional
        Filter by programming language key.

    Returns
    -------
    list[dict]
        Each dict contains ``key``, ``name``, ``language``, and ``type``.
    """
    result = [
        {"key": k, "name": v["name"], "language": v["language"], "type": v["type"]}
        for k, v in FRAMEWORK_DB.items()
    ]
    if language:
        result = [f for f in result if f["language"] == language]
    return result


def get_methodologies() -> list[dict[str, str]]:
    """
    Return a list of all development methodologies.

    Returns
    -------
    list[dict]
        Each dict contains ``key`` and ``name``.
    """
    return [{"key": k, "name": v["name"]} for k, v in METHODOLOGY_DB.items()]


def get_language_info(language: str) -> dict[str, Any]:
    """
    Return detailed information about a programming language.

    Parameters
    ----------
    language : str
        Language key from the LANGUAGE_DB.

    Returns
    -------
    dict
        Full language record or a minimal fallback dict.
    """
    info = LANGUAGE_DB.get(language)
    if info:
        return {"key": language, **info}
    return {
        "key": language,
        "name": language.title(),
        "extension": language,
        "comment_syntax": "#",
        "file_extension": f".{language}",
        "boilerplate": "",
        "best_practices": [],
        "common_frameworks": [],
    }


# =============================================================================
# PRIVATE HELPERS FOR SCAFFOLDING
# =============================================================================

def _generate_setup_commands(language: str, framework: str, project_name: str) -> list[str]:
    """Generate setup commands for a given language/framework combo."""
    commands: list[str] = []

    if language == "python":
        commands.extend([
            f"python -m venv venv",
            f"source venv/bin/activate  # Windows: venv\\Scripts\\activate",
            f"pip install -r requirements.txt" if framework else f"pip install -e .",
        ])
        if framework == "fastapi":
            commands.append("uvicorn main:app --reload")
        elif framework == "django":
            commands.extend(["python manage.py migrate", "python manage.py runserver"])
        elif framework == "flask":
            commands.append("flask run")

    elif language in ("javascript", "typescript"):
        commands.extend([
            "npm install",
        ])
        if framework in ("react", "vue", "svelte", "angular"):
            commands.append("npm run dev")
        elif framework in ("express", "fastify", "nestjs"):
            commands.append("npm start")
        elif framework in ("nextjs", "nuxtjs"):
            commands.append("npm run dev")

    elif language == "go":
        commands.extend([
            "go mod tidy",
            "go run main.go",
        ])

    elif language == "rust":
        commands.extend([
            "cargo build",
            "cargo run",
        ])

    elif language == "java":
        commands.extend([
            "./mvnw spring-boot:run" if framework == "spring" else "javac Main.java && java Main",
        ])

    elif language == "csharp":
        commands.extend([
            "dotnet restore",
            "dotnet run",
        ])

    elif language == "ruby":
        commands.extend([
            "bundle install",
            "rails server" if framework == "rails" else "ruby app.rb",
        ])

    elif language == "php":
        commands.extend([
            "composer install",
            "php artisan serve" if framework == "laravel" else "php -S localhost:8000",
        ])

    elif language == "dart" and framework == "flutter":
        commands.extend([
            "flutter pub get",
            "flutter run",
        ])

    elif language == "swift":
        commands.extend([
            "swift build",
            "swift run",
        ])

    elif language == "kotlin":
        commands.extend([
            "./gradlew build",
            "./gradlew run",
        ])

    return commands if commands else ["# No specific setup commands available"]


def _generate_tree_text(files: list[dict[str, str]]) -> str:
    """Generate an ASCII tree representation from a file list."""
    tree = _build_file_tree(files)

    def render(node: dict, prefix: str = "") -> list[str]:
        lines: list[str] = []
        items = sorted(node.items(), key=lambda x: (x[1] is not None, x[0]))
        for i, (name, subtree) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}")
            if subtree is not None:
                extension = "    " if is_last else "│   "
                lines.extend(render(subtree, prefix + extension))
        return lines

    return "\\n".join(render(tree))


def _generate_dockerfile(language: str, framework: str = "") -> str:
    """Generate a Dockerfile for a given language/framework."""
    dockerfiles = {
        "python": f"""FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
        "javascript": f"""FROM node:20-alpine

WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .

EXPOSE 3000
CMD ["npm", "start"]
""",
        "typescript": f"""FROM node:20-alpine

WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
""",
        "go": f"""FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum .
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o main .

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/main .
EXPOSE 8080
CMD ["./main"]
""",
        "rust": f"""FROM rust:1.75 AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock .
RUN mkdir src && echo "fn main() {{}}" > src/main.rs
RUN cargo build --release && rm -rf src
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/target/release/app .
EXPOSE 8080
CMD ["./app"]
""",
        "java": f"""FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY . .
RUN ./mvnw clean package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
""",
        "csharp": f"""FROM mcr.microsoft.com/dotnet/sdk:8.0 AS builder
WORKDIR /src
COPY . .
RUN dotnet restore
RUN dotnet publish -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=builder /app/publish .
EXPOSE 8080
ENTRYPOINT ["dotnet", "app.dll"]
""",
        "ruby": f"""FROM ruby:3.2-slim
WORKDIR /app
COPY Gemfile Gemfile.lock .
RUN bundle install
COPY . .
EXPOSE 3000
CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]
""",
        "php": f"""FROM php:8.3-apache
WORKDIR /var/www/html
COPY . .
RUN docker-php-ext-install pdo pdo_mysql
EXPOSE 80
""",
    }
    return dockerfiles.get(language, f"# Dockerfile for {language}\\n# Please customize based on your needs\\n")


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "generate_code",
    "review_code",
    "debug_code",
    "design_architecture",
    "scaffold_project",
    "explain_code",
    "convert_code",
    "generate_tests",
    "get_languages",
    "get_frameworks",
    "get_methodologies",
    "get_language_info",
    "LANGUAGE_DB",
    "FRAMEWORK_DB",
    "METHODOLOGY_DB",
]