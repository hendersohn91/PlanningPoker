// file service: https://www.twilio.com/blog/transfer-files-data-javascript-applications-angular-node-js
import { BrowserModule } from '@angular/platform-browser';
import { NgModule, inject, provideAppInitializer } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { CookieService } from 'ngx-cookie-service';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './login/login.component';
import { PokerlistComponent } from './pokerlist/pokerlist.component';
import { UserService } from './services/user.service';
import { ConfigService } from './services/config.service';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatButtonModule } from '@angular/material/button';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatInputModule } from '@angular/material/input';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { WebsocketService } from './services/websocket.service';
import {MatCheckboxModule} from '@angular/material/checkbox';
import { MatTableModule } from '@angular/material/table';
import { MatDialogModule } from '@angular/material/dialog';
import { JiraStoryComponent } from './jira-story/jira-story.component';
import { JiraNoteDialogComponent } from './jira-story/jira-note-dialog/jira-note-dialog.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { CreateUserDialogComponent } from './login/create-user-dialog/create-user-dialog.component';
import { MatCardModule } from '@angular/material/card';
import { RestartVotingDialogComponent } from './jira-story/restart-voting-dialog/restart-voting-dialog.component';

function initializeApp(appConfig: ConfigService): () => Promise<void> {
    return () => appConfig.loadConfig();
}

@NgModule({ declarations: [
        LoginComponent,
        PokerlistComponent,
        JiraStoryComponent,
        JiraNoteDialogComponent,
        CreateUserDialogComponent,
        RestartVotingDialogComponent
    ], imports: [BrowserModule,
        AppRoutingModule,
        FormsModule,
        BrowserAnimationsModule,
        MatButtonModule, MatGridListModule, MatInputModule, MatExpansionModule, MatButtonToggleModule, MatBadgeModule,
        MatDividerModule, MatToolbarModule, MatIconModule, MatProgressBarModule, MatTableModule, MatDialogModule, MatFormFieldModule,
        MatAutocompleteModule, ReactiveFormsModule, MatCardModule, MatCheckboxModule], providers: [
        CookieService,
        UserService,
        ConfigService,
        WebsocketService,
        provideAppInitializer(() => {
        const initializerFn = (initializeApp)(inject(ConfigService));
        return initializerFn();
      }),
        provideHttpClient(withInterceptorsFromDi())
    ] })
export class AppModule {
}
