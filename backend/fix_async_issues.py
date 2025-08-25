#!/usr/bin/env python3
"""
Script to find and fix async/await issues in the transcription platform
Run this from your backend directory: python fix_async_issues.py
"""

import os
import re
import glob

def find_async_issues():
    """Find common async/await issues in the codebase"""
    issues = []
    
    # Find all Python files
    py_files = glob.glob("**/*.py", recursive=True)
    
    for file_path in py_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Check for missing await on _get_audio_duration
                if '_get_audio_duration(' in line and 'await' not in line and 'async def' not in line:
                    issues.append({
                        'file': file_path,
                        'line': line_num,
                        'issue': 'Missing await on _get_audio_duration',
                        'code': line.strip(),
                        'fix': line.strip().replace('self._get_audio_duration', 'await self._get_audio_duration')
                                            .replace('transcription_service._get_audio_duration', 'await transcription_service._get_audio_duration')
                    })
                
                # Check for 'wait' instead of 'await'
                if re.search(r'\bwait\s+\w+\._store_in_qdrant', line):
                    issues.append({
                        'file': file_path,
                        'line': line_num,
                        'issue': 'Typo: "wait" instead of "await"',
                        'code': line.strip(),
                        'fix': line.strip().replace('wait ', 'await ')
                    })
                
                # Check for other potential coroutine issues
                if '<coroutine object' in line:
                    issues.append({
                        'file': file_path,
                        'line': line_num,
                        'issue': 'Potential coroutine object detected',
                        'code': line.strip(),
                        'fix': 'Check if this line needs await'
                    })
        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return issues

def create_backup_and_fix(file_path, original_line, fixed_line, line_num):
    """Create backup and apply fix"""
    try:
        # Create backup
        backup_path = f"{file_path}.backup"
        if not os.path.exists(backup_path):
            with open(file_path, 'r', encoding='utf-8') as original:
                with open(backup_path, 'w', encoding='utf-8') as backup:
                    backup.write(original.read())
        
        # Apply fix
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_num <= len(lines):
            old_line = lines[line_num - 1]
            if original_line.strip() in old_line:
                lines[line_num - 1] = old_line.replace(original_line.strip(), fixed_line)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                return True
    
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
    
    return False

def main():
    """Main function to find and optionally fix issues"""
    print("🔍 Scanning for async/await issues...")
    
    issues = find_async_issues()
    
    if not issues:
        print("✅ No async/await issues found!")
        return
    
    print(f"\n❌ Found {len(issues)} potential issues:")
    print("=" * 60)
    
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. {issue['issue']}")
        print(f"   File: {issue['file']}:{issue['line']}")
        print(f"   Code: {issue['code']}")
        if 'fix' in issue and issue['fix'] != issue['code']:
            print(f"   Fix:  {issue['fix']}")
    
    print("\n" + "=" * 60)
    
    # Ask if user wants to apply fixes
    while True:
        choice = input("\nDo you want to apply these fixes automatically? (y/n/s for selective): ").lower().strip()
        
        if choice == 'n':
            print("No changes made. Please fix these issues manually.")
            break
        elif choice == 'y':
            print("\n🔧 Applying all fixes...")
            fixed_count = 0
            
            for issue in issues:
                if 'fix' in issue and issue['fix'] != issue['code'] and issue['fix'] != 'Check if this line needs await':
                    if create_backup_and_fix(issue['file'], issue['code'], issue['fix'], issue['line']):
                        print(f"✅ Fixed: {issue['file']}:{issue['line']}")
                        fixed_count += 1
                    else:
                        print(f"❌ Failed to fix: {issue['file']}:{issue['line']}")
            
            print(f"\n🎉 Applied {fixed_count} fixes out of {len(issues)} issues.")
            print("Backup files created with .backup extension.")
            break
        elif choice == 's':
            print("\n🔧 Selective fixing mode...")
            fixed_count = 0
            
            for issue in issues:
                if 'fix' in issue and issue['fix'] != issue['code'] and issue['fix'] != 'Check if this line needs await':
                    print(f"\nFix this issue? {issue['issue']}")
                    print(f"File: {issue['file']}:{issue['line']}")
                    print(f"From: {issue['code']}")
                    print(f"To:   {issue['fix']}")
                    
                    if input("Apply this fix? (y/n): ").lower().strip() == 'y':
                        if create_backup_and_fix(issue['file'], issue['code'], issue['fix'], issue['line']):
                            print("✅ Fixed!")
                            fixed_count += 1
                        else:
                            print("❌ Failed to apply fix")
                    else:
                        print("⏭️  Skipped")
            
            print(f"\n🎉 Applied {fixed_count} fixes.")
            break
        else:
            print("Please enter 'y' for yes, 'n' for no, or 's' for selective.")

if __name__ == "__main__":
    main()