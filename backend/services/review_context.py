"""Changed-line-first prompt context; complete snapshots remain in scoped evidence tools."""


def build_focused_context(files: list[dict], changed_lines: dict, budget: int = 28000) -> str | None:
    """Keep every changed line, then add nearby code fairly across files.

    None means the entire set cannot fit safely: caller retains its original renderer.
    This selects the initial prompt only; it never alters snapshots, diffs or tool reads.
    """
    records=[]
    for item in files:
        source=item.get('src_content') or ''
        if not source:
            continue
        lines=source.splitlines()
        changed={line for line in changed_lines.get(item['path'],set()) if 1<=line<=len(lines)}
        header=f"\n{'='*60}\nFILE: {item['path']} ({item['change_type']}) — {len(changed)} changed lines\n{'='*60}\n"
        records.append((header,lines,changed))
    if not records:
        return ''

    def numbered(lines, selected, changed):
        output=[];previous=0
        for number in sorted(selected):
            if number>previous+1:
                output.append(f'       ... lines {previous+1}-{number-1} omitted; full source available via dashboard_context')
            marker='[NEW] ' if number in changed else '       '
            output.append(f'L{number:4d}:{marker}{lines[number-1]}')
            previous=number
        if previous<len(lines):
            output.append(f'       ... lines {previous+1}-{len(lines)} omitted; full source available via dashboard_context')
        return '\n'.join(output)

    def render(selections):
        return '\n'.join(header+numbered(lines,selected,changed)
                         for (header,lines,changed),selected in zip(records,selections))

    full=render([set(range(1,len(lines)+1)) for _,lines,_ in records])
    if len(full)<=budget:
        return full
    selected=[set(changed) for _,_,changed in records]
    essential=render(selected)
    if len(essential)>budget:
        return None
    # Round-robin context expansion prevents the first large file from crowding out
    # changes later in the PR. Extra space covers inserted gap markers conservatively.
    remaining=budget-len(essential)
    candidates=[]
    for _,lines,changed in records:
        near=sorted({line+offset for line in changed for offset in range(-12,13)
                     if 1<=line+offset<=len(lines)}-changed,
                    key=lambda line:(min(abs(line-c) for c in changed),line)) if changed else []
        head=[line for line in range(1,min(len(lines),40)+1) if line not in changed and line not in near]
        candidates.append(iter(near+head))
    pending=set(range(len(records)))
    while pending:
        for index in sorted(pending):
            try:line=next(candidates[index])
            except StopIteration:
                pending.remove(index);continue
            cost=len(records[index][1][line-1])+110
            if cost<=remaining:
                selected[index].add(line);remaining-=cost
    result=render(selected)
    return result if len(result)<=budget else None
