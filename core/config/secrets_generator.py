"""
Gerador de secrets seguros para API_SECRET_KEY e JWT_SECRET_KEY.
"""

import secrets
import string
from pathlib import Path


class SecretsGenerator:
    """
    Gera secrets criptograficamente seguros.
    """
    
    @staticmethod
    def generate_secret(length: int = 32) -> str:
        """
        Gera um secret aleatório seguro.
        
        Args:
            length: Tamanho do secret (padrão: 32 bytes = 256 bits)
            
        Returns:
            Secret em formato URL-safe base64
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_hex_secret(length: int = 32) -> str:
        """
        Gera um secret em formato hexadecimal.
        
        Args:
            length: Tamanho do secret em bytes
            
        Returns:
            Secret em formato hex
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_password(length: int = 24, 
                         use_special: bool = True) -> str:
        """
        Gera uma senha forte.
        
        Args:
            length: Tamanho da senha
            use_special: Incluir caracteres especiais
            
        Returns:
            Senha gerada
        """
        alphabet = string.ascii_letters + string.digits
        if use_special:
            alphabet += '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    @staticmethod
    def update_env_file(env_path: str, secrets_dict: dict):
        """
        Atualiza arquivo .env com novos secrets.
        
        Args:
            env_path: Caminho para o arquivo .env
            secrets_dict: Dict com {KEY: value}
        """
        env_file = Path(env_path)
        
        if not env_file.exists():
            raise FileNotFoundError(f".env não encontrado: {env_path}")
        
        # Ler arquivo
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Atualizar linhas
        updated_lines = []
        updated_keys = set()
        
        for line in lines:
            updated = False
            for key, value in secrets_dict.items():
                if line.startswith(f'{key}='):
                    # Substituir valor
                    updated_lines.append(f'{key}={value}\n')
                    updated_keys.add(key)
                    updated = True
                    break
            
            if not updated:
                updated_lines.append(line)
        
        # Adicionar keys que não existiam
        for key, value in secrets_dict.items():
            if key not in updated_keys:
                updated_lines.append(f'\n# Gerado automaticamente\n{key}={value}\n')
        
        # Escrever de volta
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        print(f"✅ Arquivo {env_path} atualizado com sucesso!")


def main():
    """Gera secrets e atualiza .env"""
    print("🔐 Gerador de Secrets\n")
    
    # Gerar secrets
    api_secret = SecretsGenerator.generate_secret(32)
    jwt_secret = SecretsGenerator.generate_secret(32)
    
    print("Secrets gerados:")
    print(f"  API_SECRET_KEY: {api_secret}")
    print(f"  JWT_SECRET_KEY: {jwt_secret}")
    print()
    
    # Perguntar se deve atualizar .env
    response = input("Deseja atualizar o arquivo .env? (s/n): ")
    
    if response.lower() == 's':
        env_path = '/app/maveretta/.env'
        
        secrets_dict = {
            'API_SECRET_KEY': api_secret,
            'JWT_SECRET_KEY': jwt_secret
        }
        
        try:
            SecretsGenerator.update_env_file(env_path, secrets_dict)
            print("\n✅ Secrets adicionados ao .env com sucesso!")
        except Exception as e:
            print(f"\n❌ Erro ao atualizar .env: {e}")
    else:
        print("\n⚠️  Secrets não foram salvos. Adicione manualmente ao .env:")
        print(f"API_SECRET_KEY={api_secret}")
        print(f"JWT_SECRET_KEY={jwt_secret}")


if __name__ == '__main__':
    main()
