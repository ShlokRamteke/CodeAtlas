from __future__ import annotations

from app.parser.ast_parser import ASTCodeParser


def test_typescript_ast_parsing() -> None:
    parser = ASTCodeParser()
    code = """
    import React, { useState } from 'react';
    import { UserService } from './services/UserService';
    import axios from 'axios';

    export interface UserProfile {
        id: string;
        username: string;
    }

    export type AuthToken = string;

    export class AuthService {
        private secret: string;

        constructor(secret: string) {
            this.secret = secret;
        }

        async login(user: UserProfile): Promise<AuthToken> {
            return "token_123";
        }
    }

    export const validateToken = (token: AuthToken): boolean => {
        return token.length > 0;
    };
    """
    result = parser.parse_code("src/auth/AuthService.ts", code)
    assert result.language == "typescript"

    symbol_names = {s.name: s.kind for s in result.symbols}
    assert "UserProfile" in symbol_names
    assert symbol_names["UserProfile"] == "interface"
    assert "AuthToken" in symbol_names
    assert symbol_names["AuthToken"] == "type"
    assert "AuthService" in symbol_names
    assert symbol_names["AuthService"] == "class"
    assert "login" in symbol_names
    assert symbol_names["login"] == "method"
    assert "validateToken" in symbol_names
    assert symbol_names["validateToken"] == "function"

    deps = {(d.target_path, d.imported_symbol, d.kind) for d in result.dependencies}
    assert ("react", "useState", "external") in deps
    assert ("./services/UserService", "UserService", "relative") in deps
    assert ("axios", "axios", "external") in deps


def test_python_ast_parsing() -> None:
    parser = ASTCodeParser()
    code = """
    import os
    from typing import List, Optional
    from app.models.user import User

    class OrderProcessor:
        \"\"\"High level processor for customer checkout orders.\"\"\"

        async def process(self, order_id: str) -> bool:
            \"\"\"Executes order settlement.\"\"\"
            return True

    def calculate_tax(subtotal: float, rate: float = 0.1) -> float:
        return subtotal * rate
    """
    result = parser.parse_code("backend/app/orders/processor.py", code)
    assert result.language == "python"

    symbol_names = {s.name: (s.kind, s.docstring) for s in result.symbols}
    assert "OrderProcessor" in symbol_names
    assert symbol_names["OrderProcessor"][0] == "class"
    assert "High level processor" in (symbol_names["OrderProcessor"][1] or "")

    assert "process" in symbol_names
    assert symbol_names["process"][0] == "function"
    assert "Executes order settlement" in (symbol_names["process"][1] or "")

    assert "calculate_tax" in symbol_names
    assert symbol_names["calculate_tax"][0] == "function"

    deps = {(d.target_path, d.imported_symbol, d.kind) for d in result.dependencies}
    assert ("os", None, "external") in deps
    assert ("app.models.user", "User", "internal") in deps
