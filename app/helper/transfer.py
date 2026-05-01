import os
import shutil
from pathlib import Path
from loguru import logger

class TransferHelper:
    """处理目录文件系统底层的刮削转移（硬链接/移动/复制）"""
    
    @staticmethod
    def transfer(src_path: str, dest_path: str, mode: str = "hardlink") -> bool:
        """
        跨磁盘操作或同盘硬链接分配
        - mode: 'hardlink', 'copy', 'move'
        """
        src = Path(src_path)
        dest = Path(dest_path)
        
        if not src.exists():
            logger.error(f"源文件/目录不存在: {src}")
            return False
            
        # 如果是目录，递归处理
        if src.is_dir():
            if not dest.exists():
                dest.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                # 递归处理
                success = TransferHelper.transfer(str(item), str(dest / item.name), mode)
                if not success:
                    return False
            # 移动模式下，清空原文件夹后删除
            if mode == "move":
                try:
                    src.rmdir()
                except Exception as e:
                    logger.warning(f"目录非空或权限不足，无法删除源目录 {src}: {e}")
            return True
            
        # 如果是文件
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            
        # 对已存在文件直接覆盖或跳过
        if dest.exists():
            if dest.stat().st_size == src.stat().st_size:
                # logger.debug(f"目标文件已存在且大小相同，跳过: {dest}")
                return True
            else:
                dest.unlink()
                
        try:
            if mode == "hardlink":
                try:
                    os.link(src, dest)
                except OSError as e:
                    # [Errno 18] Invalid cross-device link 等错误
                    logger.warning(f"硬链接失败，退化为复制模式 ({e})。源盘可能与目标盘不在同一个卷: \n -> src:{src} \n -> dst:{dest}")
                    shutil.copy2(src, dest)
            elif mode == "move":
                shutil.move(str(src), str(dest))
            elif mode == "copy":
                shutil.copy2(src, dest)
            else:
                logger.error(f"不支持的转移模式: {mode}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"文件转移失败 [{mode}]: {src} -> {dest} \n {e}")
            return False

    @staticmethod
    def is_media_file(filename: str) -> bool:
        """判断是否是常见的视频媒体文件"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in ['.mp4', '.mkv', '.avi', '.ts', '.rmvb', '.iso', '.m2ts', '.wmv']
        
    @staticmethod
    def is_subtitle_file(filename: str) -> bool:
        """判断是否是常见的字幕文件"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in ['.ass', '.srt', '.ssa', '.idx', '.sub']
