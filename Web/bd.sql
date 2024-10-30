CREATE TABLE IF NOT EXISTS Usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                                
    email VARCHAR(255) NULL,                                             
    senha VARCHAR(255) NULL,                                             
    nome VARCHAR(255) NULL,                                          
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,                     
    data_ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP,          
    status TEXT CHECK(status in ('ativo', 'bloqueado')) DEFAULT 'ativo', 
    UNIQUE (email)                                                       
);


