#!/usr/bin/env python3
"""
Sistema de Backup Automatico para MQTT Dashboard

Este script realiza copias de seguridad automaticas de la base de datos SQLite.
Puede ejecutarse como script independiente o integrarse con el scheduler.

Funcionalidades:
- Backup incremental con timestamp
- Rotacion de backups antiguos (por defecto mantiene 7)
- Compresion de archivos de backup
- Logging detallado
- Restauracion desde backup

Uso:
    python backup_db.py                    # Backup manual
    python backup_db.py --restore          # Restaurar ultimo backup
    python backup_db.py --list             # Listar backups disponibles
"""

import os
import sys
import shutil
import gzip
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

# Configuracion de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracion por defecto
DEFAULT_CONFIG = {
    'backup_dir': 'backups',
    'database_file': 'dashboard.db',
    'max_backups': 7,
    'compression': True,
    'enabled': False,
    'interval_hours': 24
}

class BackupManager:
    """Gestor de copias de seguridad de la base de datos."""
    
    def __init__(self, backup_dir: str = None, db_file: str = None, max_backups: int = None):
        """Inicializar el gestor de backups."""
        self.project_root = Path(__file__).parent  # Directorio del script (MQTT_Dashboard)
        self.backup_dir = backup_dir or DEFAULT_CONFIG['backup_dir']
        self.db_file = db_file or DEFAULT_CONFIG['database_file']
        self.max_backups = max_backups or DEFAULT_CONFIG['max_backups']
        
        self.backup_path = self.project_root / self.backup_dir
        self.db_path = self.project_root / self.db_file
        
        # Crear directorio de backups si no existe
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[BACKUP] Directorio: {self.backup_path}")
        logger.info(f"[DB] Archivo: {self.db_path}")
    
    def get_backup_filename(self) -> str:
        """Generar nombre de archivo con timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"dashboard_backup_{timestamp}.db"
    
    def list_backups(self) -> List[Path]:
        """Listar todos los archivos de backup disponibles."""
        if not self.backup_path.exists():
            return []
        
        backups = list(self.backup_path.glob("dashboard_backup_*.db*"))
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return backups
    
    def create_backup(self) -> Optional[Path]:
        """Crear una copia de seguridad de la base de datos."""
        if not self.db_path.exists():
            logger.error(f"[ERROR] Base de datos no encontrada: {self.db_path}")
            return None
        
        try:
            backup_file = self.backup_path / self.get_backup_filename()
            
            logger.info(f"[BACKUP] Creando: {backup_file.name}")
            shutil.copy2(self.db_path, backup_file)
            
            # Comprimir si esta habilitado
            if DEFAULT_CONFIG['compression']:
                compressed_file = Path(str(backup_file) + '.gz')
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_file.unlink()
                backup_file = compressed_file
                logger.info(f"[BACKUP] Comprimido: {backup_file.name}")
            
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            logger.info(f"[BACKUP] Tamano: {size_mb:.2f} MB")
            
            # Rotar backups antiguos
            self.rotate_backups()
            
            logger.info(f"[OK] Backup creado: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"[ERROR] Backup: {e}")
            return None
    
    def rotate_backups(self):
        """Eliminar backups antiguos excediendo el limite."""
        backups = self.list_backups()
        
        if len(backups) > self.max_backups:
            to_remove = backups[self.max_backups:]
            logger.info(f"[CLEANUP] Eliminando {len(to_remove)} backups antiguos...")
            
            for backup in to_remove:
                try:
                    backup.unlink()
                    logger.info(f"   Eliminado: {backup.name}")
                except Exception as e:
                    logger.warning(f"   Error: {e}")
    
    def restore_backup(self, backup_file: Path = None) -> bool:
        """Restaurar base de datos desde un backup."""
        if backup_file is None:
            backups = self.list_backups()
            if not backups:
                logger.error("[ERROR] No hay backups disponibles")
                return False
            backup_file = backups[0]
        
        try:
            logger.info(f"[RESTORE] Desde: {backup_file}")
            
            if str(backup_file).endswith('.gz'):
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_file, self.db_path)
            
            logger.info("[OK] Base de datos restaurada")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Restaurar: {e}")
            return False
    
    def get_backup_info(self) -> dict:
        """Obtener informacion sobre los backups."""
        backups = self.list_backups()
        
        info = {
            'total_backups': len(backups),
            'latest_backup': None,
            'oldest_backup': None,
            'total_size_mb': 0
        }
        
        if backups:
            info['latest_backup'] = backups[0].name
            info['oldest_backup'] = backups[-1].name
            for backup in backups:
                info['total_size_mb'] += backup.stat().st_size / (1024 * 1024)
        
        return info
    
    def delete_old_backups(self, days: int = 30):
        """Eliminar backups mas antiguos que X dias."""
        cutoff = datetime.now() - timedelta(days=days)
        backups = self.list_backups()
        
        deleted = 0
        for backup in backups:
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            if mtime < cutoff:
                backup.unlink()
                deleted += 1
        
        logger.info(f"[CLEANUP] Eliminados {deleted} backups > {days} dias")
        return deleted
    
    def delete_backup(self, filename: str) -> bool:
        """Eliminar un archivo de backup especifico."""
        try:
            backup_file = self.backup_path / filename
            if backup_file.exists():
                backup_file.unlink()
                logger.info(f"[DELETE] Eliminado: {filename}")
                return True
            else:
                logger.warning(f"[DELETE] No encontrado: {filename}")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Eliminar backup: {e}")
            return False
    
    def get_backups_for_ui(self) -> list:
        """Obtener lista formateada para la interfaz de usuario."""
        backups = self.list_backups()
        result = []
        
        for backup in backups:
            try:
                size_bytes = backup.stat().st_size
                size_mb = round(size_bytes / (1024 * 1024), 2)
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                
                # Generar display name
                name_parts = backup.name.replace('dashboard_backup_', '').replace('.db.gz', '').replace('.db', '')
                display = mtime.strftime('%Y-%m-%d %H:%M')
                
                result.append({
                    'filename': backup.name,
                    'size_mb': size_mb,
                    'datetime': mtime.isoformat(),
                    'display': display,
                    'is_compressed': str(backup).endswith('.gz')
                })
            except Exception as e:
                logger.warning(f"[UI] Error procesando backup {backup.name}: {e}")
        
        return result


def run_scheduled_backup():
    """Ejecutar backup para ser llamado desde el scheduler."""
    manager = BackupManager()
    result = manager.create_backup()
    return result is not None


def main():
    """Funcion principal con interfaz de linea de comandos."""
    parser = argparse.ArgumentParser(
        description='Sistema de Backup para MQTT Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
    python backup_db.py                  # Crear backup
    python backup_db.py --restore        # Restaurar ultimo backup
    python backup_db.py --list           # Listar backups
    python backup_db.py --delete-old 30  # Eliminar backups de mas de 30 dias
        """
    )
    
    parser.add_argument('--backup', action='store_true', help='Crear backup')
    parser.add_argument('--restore', action='store_true', help='Restaurar backup')
    parser.add_argument('--list', action='store_true', help='Listar backups')
    parser.add_argument('--delete-old', type=int, metavar='DAYS', help='Eliminar backups antiguos')
    parser.add_argument('--auto', action='store_true', help='Ejecutar backup automatico')
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n[OPTIONS]")
        print("   --backup    Crear un nuevo backup")
        print("   --restore   Restaurar el ultimo backup")
        print("   --list      Listar backups disponibles")
        print("   --auto      Ejecutar backup automatico")
        print("\n[INFO] Creando backup por defecto...")
        manager.create_backup()
        return
    
    if args.backup or args.auto:
        manager.create_backup()
    
    if args.restore:
        manager.restore_backup()
    
    if args.list:
        backups = manager.list_backups()
        info = manager.get_backup_info()
        
        print(f"\n[BACKUPS] Disponibles: {info['total_backups']}")
        print(f"[SIZE] Total: {info['total_size_mb']:.2f} MB\n")
        
        for i, backup in enumerate(backups[:10]):
            size_mb = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"   {i+1}. {backup.name} ({size_mb:.2f} MB) - {mtime.strftime('%Y-%m-%d %H:%M')}")
        
        if len(backups) > 10:
            print(f"   ... y {len(backups) - 10} mas")
    
    if args.delete_old:
        manager.delete_old_backups(args.delete_old)


if __name__ == '__main__':
    main()
