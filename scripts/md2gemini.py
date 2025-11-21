#!/usr/bin/env python3
"""
Markdown to Gemtext converter for Hugo blogs.
Converts Hugo content files to Gemini protocol format.
"""

import os
import re
import yaml
from pathlib import Path
from datetime import datetime


def parse_frontmatter(content):
    """Extract YAML frontmatter and body from markdown file."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return frontmatter or {}, body
            except yaml.YAMLError:
                pass
    return {}, content


def convert_links(text):
    """Convert markdown links to gemini links."""
    lines = []
    current_text = text

    # Find all markdown links
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'

    # Split text by links and process
    parts = re.split(link_pattern, current_text)

    result_lines = []
    collected_links = []
    i = 0

    while i < len(parts):
        if i + 2 < len(parts):
            # Text before link
            text_part = parts[i]
            link_text = parts[i + 1]
            link_url = parts[i + 2]

            result_lines.append(text_part)
            collected_links.append(f"=> {link_url} {link_text}")
            i += 3
        else:
            result_lines.append(parts[i])
            i += 1

    final_text = ''.join(result_lines)

    # Add collected links after paragraph
    if collected_links:
        final_text += '\n' + '\n'.join(collected_links)

    return final_text


def convert_markdown_to_gemtext(content):
    """Convert markdown content to gemtext format."""
    frontmatter, body = parse_frontmatter(content)

    lines = []

    # Add title from frontmatter
    if frontmatter.get('title'):
        lines.append(f"# {frontmatter['title']}")
        lines.append("")

    # Add date if present
    if frontmatter.get('date'):
        date = frontmatter['date']
        if isinstance(date, datetime):
            date = date.strftime('%Y-%m-%d')
        lines.append(f"Data: {date}")
        lines.append("")

    # Add summary if present
    if frontmatter.get('summary'):
        lines.append(frontmatter['summary'])
        lines.append("")

    # Process body
    in_code_block = False
    code_block_lines = []

    for line in body.split('\n'):
        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                lines.append('```')
                in_code_block = False
            else:
                lines.append('```')
                in_code_block = True
            continue

        if in_code_block:
            lines.append(line)
            continue

        # Skip Hugo shortcodes
        if '{{<' in line or '{{%' in line:
            continue

        # Convert headers
        if line.startswith('#'):
            # Gemini supports up to 3 levels
            match = re.match(r'^(#{1,3})\s*(.+)$', line)
            if match:
                level = len(match.group(1))
                text = match.group(2)
                lines.append(f"{'#' * level} {text}")
                continue

        # Convert bold headers (like **Heading**)
        if line.strip().startswith('**') and line.strip().endswith('**'):
            text = line.strip()[2:-2]
            lines.append(f"## {text}")
            continue

        # Convert list items
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:]
            # Remove inline formatting
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            text = re.sub(r'\*([^*]+)\*', r'\1', text)
            text = re.sub(r'`([^`]+)`', r'\1', text)
            lines.append(f"* {text}")
            continue

        # Convert blockquotes
        if line.strip().startswith('>'):
            text = line.strip()[1:].strip()
            lines.append(f"> {text}")
            continue

        # Regular text - remove inline formatting
        text = line
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # italic
        text = re.sub(r'`([^`]+)`', r'\1', text)        # code
        text = re.sub(r':[\w]+:', '', text)             # emoji shortcodes

        # Convert links
        text = convert_links(text)

        lines.append(text)

    return '\n'.join(lines)


def process_hugo_content(content_dir, output_dir):
    """Process all Hugo content files and convert to gemtext."""
    content_path = Path(content_dir)
    output_path = Path(output_dir)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    processed = 0

    # Process all markdown files
    for md_file in content_path.rglob('*.md'):
        # Skip _index.md files (they're section pages)
        if md_file.name == '_index.md':
            continue

        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Convert to gemtext
        gemtext = convert_markdown_to_gemtext(content)

        # Determine output path
        rel_path = md_file.relative_to(content_path)

        # Handle index.md in subdirectories
        if md_file.name == 'index.md':
            gem_path = output_path / rel_path.parent.with_suffix('.gmi')
        else:
            gem_path = output_path / rel_path.with_suffix('.gmi')

        # Create parent directories
        gem_path.parent.mkdir(parents=True, exist_ok=True)

        # Write gemtext file
        with open(gem_path, 'w', encoding='utf-8') as f:
            f.write(gemtext)

        print(f"Converted: {md_file} -> {gem_path}")
        processed += 1

    # Create index page
    create_gemini_index(content_path, output_path)

    print(f"\nTotal files converted: {processed}")


def create_gemini_index(content_path, output_path):
    """Create a gemini index page listing all posts."""
    lines = [
        "# Blog",
        "",
        "Witaj w wersji Gemini mojego bloga!",
        "",
        "## Posty",
        ""
    ]

    # Find all posts
    posts = []
    blog_path = content_path / 'blog'

    if blog_path.exists():
        for post_dir in blog_path.iterdir():
            if post_dir.is_dir():
                index_file = post_dir / 'index.md'
                if index_file.exists():
                    with open(index_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    frontmatter, _ = parse_frontmatter(content)

                    title = frontmatter.get('title', post_dir.name)
                    date = frontmatter.get('date', '')
                    if isinstance(date, datetime):
                        date = date.strftime('%Y-%m-%d')

                    posts.append({
                        'title': title,
                        'date': str(date),
                        'path': f"blog/{post_dir.name}.gmi"
                    })

    # Sort by date descending
    posts.sort(key=lambda x: x['date'], reverse=True)

    # Add links
    for post in posts:
        lines.append(f"=> {post['path']} [{post['date']}] {post['title']}")

    # Write index
    index_path = output_path / 'index.gmi'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Created index: {index_path}")


if __name__ == '__main__':
    import sys

    # Default paths
    script_dir = Path(__file__).parent.parent
    content_dir = script_dir / 'content'
    output_dir = script_dir / 'public_gemini'

    # Allow custom paths via arguments
    if len(sys.argv) > 1:
        content_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    print(f"Converting Hugo content to Gemini format...")
    print(f"Content directory: {content_dir}")
    print(f"Output directory: {output_dir}")
    print("")

    process_hugo_content(content_dir, output_dir)
