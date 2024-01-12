Refactoring Types: ['Extract Interface']
/src/com/jetbrains/edu/coursecreator/actions/CCRename.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.jetbrains.edu.coursecreator.actions;

import com.intellij.ide.IdeView;
import com.intellij.ide.projectView.ProjectView;
import com.intellij.ide.util.DirectoryChooserUtil;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.actionSystem.LangDataKeys;
import com.intellij.openapi.actionSystem.Presentation;
import com.intellij.openapi.project.DumbAwareAction;
import com.intellij.openapi.project.Project;
import com.intellij.psi.PsiDirectory;
import com.intellij.psi.PsiFile;
import com.jetbrains.edu.courseFormat.Course;
import com.jetbrains.edu.coursecreator.CCProjectService;
import org.jetbrains.annotations.NotNull;

import javax.swing.*;

public abstract class CCRename extends DumbAwareAction {
  protected CCRename(String text, String description, Icon icon) {
    super(text, description, icon);
  }

  @Override
  public void update(@NotNull AnActionEvent event) {
    if (!CCProjectService.setCCActionAvailable(event)) {
      return;
    }
    final Presentation presentation = event.getPresentation();
    final Project project = event.getData(CommonDataKeys.PROJECT);
    if (project == null) {
      presentation.setVisible(false);
      presentation.setEnabled(false);
      return;
    }

    final IdeView view = event.getData(LangDataKeys.IDE_VIEW);
    if (view == null) {
      presentation.setVisible(false);
      presentation.setEnabled(false);
      return;
    }

    final PsiDirectory[] directories = view.getDirectories();
    if (directories.length == 0) {
      presentation.setVisible(false);
      presentation.setEnabled(false);
      return;
    }
    final PsiFile file = CommonDataKeys.PSI_FILE.getData(event.getDataContext());
    final PsiDirectory directory = DirectoryChooserUtil.getOrChooseDirectory(view);
    if (file != null ||directory == null || !directory.getName().contains(getFolderName())) {
      presentation.setEnabled(false);
      presentation.setVisible(false);
      return;
    }
    presentation.setVisible(true);
    presentation.setEnabled(true);
  }

  protected abstract String getFolderName();

  @Override
  public void actionPerformed(@NotNull AnActionEvent e) {
    final IdeView view = e.getData(LangDataKeys.IDE_VIEW);
    final Project project = e.getData(CommonDataKeys.PROJECT);

    if (view == null || project == null) {
      return;
    }
    final PsiDirectory directory = DirectoryChooserUtil.getOrChooseDirectory(view);
    if (directory == null || !directory.getName().contains(getFolderName())) {
      return;
    }
    Course course = CCProjectService.getInstance(project).getCourse();
    if (course == null) {
      return;
    }
    if (!processRename(project, directory, course)) return;
    ProjectView.getInstance(project).refresh();
  }

  protected abstract boolean processRename(Project project, PsiDirectory directory, Course course);
}


File: python/educational/course-creator/src/com/jetbrains/edu/coursecreator/actions/CCRenameLesson.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.jetbrains.edu.coursecreator.actions;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.psi.PsiDirectory;
import com.jetbrains.edu.EduNames;
import com.jetbrains.edu.courseFormat.Course;
import com.jetbrains.edu.courseFormat.Lesson;

public class CCRenameLesson extends CCRename {

  public CCRenameLesson() {
    super("Rename Lesson", "Rename Lesson", null);
  }

  @Override
  public String getFolderName() {
    return EduNames.LESSON;
  }

  @Override
  public boolean processRename(Project project, PsiDirectory directory, Course course) {
    Lesson lesson = course.getLesson(directory.getName());
    if (lesson == null) {
      return false;
    }
    String newName = Messages.showInputDialog(project, "Enter new name", "Rename " + getFolderName(), null);
    if (newName == null) {
      return false;
    }
    lesson.setName(newName);
    return true;
  }
}


File: python/educational/course-creator/src/com/jetbrains/edu/coursecreator/actions/CCRenameTask.java
/*
 * Copyright 2000-2014 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.jetbrains.edu.coursecreator.actions;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.psi.PsiDirectory;
import com.jetbrains.edu.EduNames;
import com.jetbrains.edu.courseFormat.Course;
import com.jetbrains.edu.courseFormat.Lesson;
import com.jetbrains.edu.courseFormat.Task;

public class CCRenameTask extends CCRename {
  public CCRenameTask() {
    super("Rename Task", "Rename Task", null);
  }

  @Override
  public String getFolderName() {
    return EduNames.TASK;
  }

  @Override
  public boolean processRename(Project project, PsiDirectory directory, Course course) {
    PsiDirectory lessonDir = directory.getParent();
    if (lessonDir == null || !lessonDir.getName().contains(EduNames.LESSON)) {
      return false;
    }
    Lesson lesson = course.getLesson(lessonDir.getName());
    if (lesson == null) {
      return false;
    }
    Task task = lesson.getTask(directory.getName());
    if (task == null) {
      return false;
    }
    String newName = Messages.showInputDialog(project, "Enter new name", "Rename " + getFolderName(), null);
    if (newName == null) {
      return false;
    }
    task.setName(newName);
    return true;

  }
}


File: python/educational/src/com/jetbrains/edu/courseFormat/Lesson.java
package com.jetbrains.edu.courseFormat;

import com.google.gson.annotations.Expose;
import com.google.gson.annotations.SerializedName;
import com.intellij.util.xmlb.annotations.Transient;
import com.jetbrains.edu.EduNames;
import com.jetbrains.edu.EduUtils;
import org.jetbrains.annotations.NotNull;

import java.util.ArrayList;
import java.util.List;

public class Lesson {
  @Transient
  public int id;
  @Transient
  public List<Integer> steps;
  @Transient
  public List<String> tags;
  @Transient
  Boolean is_public;
  @Expose
  @SerializedName("title")
  private String name;
  @Expose
  @SerializedName("task_list")
  public List<Task> taskList = new ArrayList<Task>();

  @Transient
  private Course myCourse = null;

  // index is visible to user number of lesson from 1 to lesson number
  private int myIndex = -1;

  public void initLesson(final Course course, boolean isRestarted) {
    setCourse(course);
    for (Task task : getTaskList()) {
      task.initTask(this, isRestarted);
    }
  }

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public int getIndex() {
    return myIndex;
  }

  public void setIndex(int index) {
    myIndex = index;
  }

  public List<Task> getTaskList() {
    return taskList;
  }

  @Transient
  public Course getCourse() {
    return myCourse;
  }

  @Transient
  public void setCourse(Course course) {
    myCourse = course;
  }

  public void addTask(@NotNull final Task task) {
    taskList.add(task);
  }

  public Task getTask(@NotNull final String name) {
    int index = EduUtils.getIndex(name, EduNames.TASK);
    List<Task> tasks = getTaskList();
    if (!EduUtils.indexIsValid(index, tasks)) {
      return null;
    }
    return tasks.get(index);
  }

}


File: python/educational/src/com/jetbrains/edu/courseFormat/Task.java
package com.jetbrains.edu.courseFormat;

import com.google.gson.annotations.Expose;
import com.google.gson.annotations.SerializedName;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.util.xmlb.annotations.Transient;
import com.jetbrains.edu.EduNames;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.HashMap;
import java.util.Map;

/**
 * Implementation of task which contains task files, tests, input file for tests
 */
public class Task {
  @Expose
  private String name;

  // index is visible to user number of task from 1 to task number
  private int myIndex;
  @Expose
  @SerializedName("task_files")
  public Map<String, TaskFile> taskFiles = new HashMap<String, TaskFile>();

  private String text;
  private Map<String, String> testsText = new HashMap<String, String>();

  @Transient private Lesson myLesson;

  public Task() {}

  public Task(@NotNull final String name) {
    this.name = name;
  }

  /**
   * Initializes state of task file
   *
   * @param lesson lesson which task belongs to
   */
  public void initTask(final Lesson lesson, boolean isRestarted) {
    setLesson(lesson);
    for (TaskFile taskFile : getTaskFiles().values()) {
      taskFile.initTaskFile(this, isRestarted);
    }
  }

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public String getText() {
    return text;
  }

  public void setText(@NotNull final String text) {
    this.text = text;
  }

  public int getIndex() {
    return myIndex;
  }

  public void setIndex(int index) {
    myIndex = index;
  }

  public Map<String, String> getTestsText() {
    return testsText;
  }

  public void setTestsTexts(String name, String text) {
    testsText.put(name, text);
  }

  public Map<String, TaskFile> getTaskFiles() {
    return taskFiles;
  }

  @Nullable
  public TaskFile getTaskFile(final String name) {
    return name != null ? taskFiles.get(name) : null;
  }

  public boolean isTaskFile(@NotNull final String fileName) {
    return taskFiles.get(fileName) != null;
  }

  public void addTaskFile(@NotNull final String name, int index) {
    TaskFile taskFile = new TaskFile();
    taskFile.setIndex(index);
    taskFiles.put(name, taskFile);
  }

  @Nullable
  public TaskFile getFile(@NotNull final String fileName) {
    return taskFiles.get(fileName);
  }

  @Transient
  public Lesson getLesson() {
    return myLesson;
  }

  @Transient
  public void setLesson(Lesson lesson) {
    myLesson = lesson;
  }

  @Nullable
  public VirtualFile getTaskDir(@NotNull final Project project) {
    String lessonDirName = EduNames.LESSON + String.valueOf(myLesson.getIndex());
    String taskDirName = EduNames.TASK + String.valueOf(myIndex);
    VirtualFile courseDir = project.getBaseDir();
    if (courseDir != null) {
      VirtualFile lessonDir = courseDir.findChild(lessonDirName);
      if (lessonDir != null) {
        return lessonDir.findChild(taskDirName);
      }
    }
    return null;
  }

  @Nullable
  public String getTaskText(@NotNull final Project project) {
    final VirtualFile taskDir = getTaskDir(project);
    if (taskDir != null) {
      final VirtualFile file = taskDir.findChild(EduNames.TASK_HTML);
      if (file == null) return null;
      final Document document = FileDocumentManager.getInstance().getDocument(file);
      if (document != null) {
        return document.getImmutableCharSequence().toString();
      }
    }

    return null;
  }

  @Nullable
  public String getTestsText(@NotNull final Project project) {
    final VirtualFile taskDir = getTaskDir(project);
    if (taskDir != null) {
      final VirtualFile file = taskDir.findChild("tests.py");
      if (file == null) return null;
      final Document document = FileDocumentManager.getInstance().getDocument(file);
      if (document != null) {
        return document.getImmutableCharSequence().toString();
      }
    }

    return null;
  }

  public Document getDocument(Project project, String name) {
    final VirtualFile taskDirectory = getTaskDir(project);
    if (taskDirectory == null) return null;
    final VirtualFile file = taskDirectory.findChild(name);
    if (file == null) return null;
    return FileDocumentManager.getInstance().getDocument(file);
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;

    Task task = (Task)o;

    if (myIndex != task.myIndex) return false;
    if (name != null ? !name.equals(task.name) : task.name != null) return false;
    if (taskFiles != null ? !taskFiles.equals(task.taskFiles) : task.taskFiles != null) return false;
    if (text != null ? !text.equals(task.text) : task.text != null) return false;
    if (testsText != null ? !testsText.equals(task.testsText) : task.testsText != null) return false;

    return true;
  }

  @Override
  public int hashCode() {
    int result = name != null ? name.hashCode() : 0;
    result = 31 * result + myIndex;
    result = 31 * result + (taskFiles != null ? taskFiles.hashCode() : 0);
    result = 31 * result + (text != null ? text.hashCode() : 0);
    result = 31 * result + (testsText != null ? testsText.hashCode() : 0);
    return result;
  }
}
