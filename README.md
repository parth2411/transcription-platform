```text
├── .gitignore
├── README.md
├── alembic.ini
├── backend
    ├── .dockerignore
    ├── Dockerfile
    ├── alembic.ini
    ├── alembic
    │   ├── README
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions
    │   │   └── da5f520624fe_initial_migration.py
    ├── app
    │   ├── __init__.py
    │   ├── config.py
    │   ├── database.py
    │   ├── main.py
    │   ├── models.py
    │   ├── routes
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── knowledge.py
    │   │   ├── railway.toml
    │   │   ├── realtime.py
    │   │   ├── realtime.py.backup
    │   │   ├── transcriptions.py
    │   │   └── users.py
    │   └── services
    │   │   ├── __init__.py
    │   │   ├── auth_service.py
    │   │   ├── file_service.py
    │   │   ├── groq_service.py
    │   │   ├── knowledge_service.py
    │   │   ├── large_video_guide.md
    │   │   └── transcription_service.py
    ├── create_tables.py
    ├── fix_async_issues.py
    ├── railway.toml
    ├── requirements.txt
    ├── scripts
    │   └── railway-setup.sh
    ├── test.py
    ├── update_account.py
    └── uploads
    │   └── 90d201be-02ef-48e1-8c32-fdad37fbef8c
    │       ├── 47203873-e24e-4e2b-8e0d-cd3db693e962.wav
    │       ├── 66374bde-0dca-4f78-b408-3a2f97d807ea.wav
    │       ├── 9390e55a-2863-4301-b1cd-2da90248d5d0.wav
    │       └── 99ff0a8b-e8fc-432f-8faa-c11b19bbd6cf.wav
├── complete_frontend_guide.md
├── complete_setup_guide.md
├── docker-compose.yml
├── frontend
    ├── .eslintrc.json
    ├── Dockerfile
    ├── next-env.d.ts
    ├── next.config.js
    ├── package-lock.json
    ├── package.json
    ├── postcss.config.js
    ├── src
    │   ├── app
    │   │   ├── (auth)
    │   │   │   ├── login
    │   │   │   │   └── page.tsx
    │   │   │   └── register
    │   │   │   │   └── page.tsx
    │   │   ├── dashboard
    │   │   │   └── page.tsx
    │   │   ├── favicon.ico
    │   │   ├── globals.css
    │   │   ├── knowledge
    │   │   │   └── page.tsx
    │   │   ├── layout.tsx
    │   │   ├── page.tsx
    │   │   ├── realtime
    │   │   │   └── page.tsx
    │   │   ├── settings
    │   │   │   └── page.tsx
    │   │   └── transcriptions
    │   │   │   ├── [id]
    │   │   │       └── page.tsx
    │   │   │   ├── new
    │   │   │       └── page.tsx
    │   │   │   └── page.tsx
    │   ├── components
    │   │   ├── auth
    │   │   │   └── AuthProvider.tsx
    │   │   ├── common
    │   │   │   ├── EmptyState.tsx
    │   │   │   ├── LoadingSpinner.tsx
    │   │   │   └── StatusBadge.tsx
    │   │   ├── layout
    │   │   │   └── DashboardLayout.tsx
    │   │   ├── providers
    │   │   │   └── QueryProvider.tsx
    │   │   ├── transcription
    │   │   │   ├── ExportActions.tsx
    │   │   │   ├── RealTimeRecorder.tsx
    │   │   │   └── URLForm.tsx
    │   │   └── ui
    │   │   │   ├── alert.tsx
    │   │   │   ├── badge.tsx
    │   │   │   ├── button.tsx
    │   │   │   ├── card.tsx
    │   │   │   ├── checkbox.tsx
    │   │   │   ├── index.ts
    │   │   │   ├── input.tsx
    │   │   │   ├── label.tsx
    │   │   │   ├── progress.tsx
    │   │   │   ├── separator.tsx
    │   │   │   ├── skeleton.tsx
    │   │   │   ├── spinner.tsx
    │   │   │   ├── switch.tsx
    │   │   │   ├── textarea.tsx
    │   │   │   └── toaster.tsx
    │   ├── hooks
    │   │   └── useApi.ts
    │   ├── lib
    │   │   └── utils.ts
    │   ├── types
    │   │   └── index.ts
    │   └── utils
    │   │   └── format.ts
    ├── tailwind.config.ts
    └── tsconfig.json
├── package-lock.json
└── package.json
```
