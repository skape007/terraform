def build_sprint_wiql(start: str,
                      end: str,
                      project: str = "DEP") -> str:
    return f"""
    SELECT
        [System.Id],
        [System.Title],
        [System.State],
        [System.ChangedDate]
    FROM WorkItems
    WHERE
        [System.TeamProject] = '{project}'
        AND [System.ChangedDate] >= '{start}'
        AND [System.ChangedDate] <= '{end}'
        AND [System.WorkItemType] <> 'Release'
        AND NOT [System.Tags] CONTAINS 'Buro'
    ORDER BY [System.ChangedDate] DESC
    """.strip()